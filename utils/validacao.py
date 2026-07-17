"""
Validação de inaudibilidade e impacto perceptivo da proteção.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np


def validar_inaudibilidade(
    original: np.ndarray,
    protegido: np.ndarray,
    sr: int,
    snr_min_db: float = 25.0,
    max_diff_abs: float = 0.15,
) -> Dict[str, Any]:
    """
    Testa se a proteção é 'quase inaudível' por métricas objetivas.

    Critérios (heurísticos, não substituem teste A/B humano):
      - SNR alto entre original e protegido
      - Diferença máxima pequena
      - Correlação temporal alta
      - Energia em banda audível (20–16kHz) da diferença baixa

    Returns:
        Dicionário com métricas e flags passou/falhou.
    """
    a = _mono(original).astype(np.float64)
    b = _mono(protegido).astype(np.float64)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]

    # Alinha atraso (all-pass) antes de SNR/correlação temporal
    a_al, b_al, lag = _alinhar(a, b, max_lag=min(n // 5, max(8, int(0.02 * sr))))
    diff = b_al - a_al
    diff_raw = b - a

    ps = float(np.mean(a_al**2)) + 1e-12
    pd = float(np.mean(diff**2)) + 1e-12
    snr = 10.0 * np.log10(ps / pd)
    max_diff = float(np.max(np.abs(diff)))
    corr = _pearson(a_al, b_al)
    corr_raw = _pearson(a, b)

    # Similaridade espectral de magnitude (melhor proxy de "invisibilidade")
    corr_spec = _correlacao_espectral(a, b, sr)

    # Energia da diferença na banda audível principal (após alinhamento)
    e_audivel = _energia_banda(diff, sr, 20.0, min(16000.0, sr / 2 - 1))
    e_ultra = _energia_banda(diff_raw, sr, min(18000.0, sr / 2 - 100), sr / 2 - 1)
    e_total = float(np.mean(diff_raw**2)) + 1e-12

    stoi_proxy = float(np.clip(0.5 * corr + 0.5 * corr_spec, 0, 1))

    # Critérios: SNR alinhado OU forte similaridade espectral (fase pode divergir)
    passou_snr = snr >= snr_min_db or corr_spec >= 0.98
    passou_diff = max_diff <= max_diff_abs or corr_spec >= 0.98
    passou_corr = corr >= 0.90 or corr_spec >= 0.97

    resultado = {
        "snr_db": float(snr),
        "snr_db_sem_alinhamento": float(
            10.0 * np.log10(
                (float(np.mean(a**2)) + 1e-12)
                / (float(np.mean(diff_raw**2)) + 1e-12)
            )
        ),
        "max_abs_diff": max_diff,
        "correlacao": corr,
        "correlacao_raw": corr_raw,
        "correlacao_espectral": corr_spec,
        "lag_alinhamento_amostras": int(lag),
        "stoi_proxy": stoi_proxy,
        "energia_diff_audivel": e_audivel,
        "energia_diff_ultrassom": e_ultra,
        "razao_ultra_sobre_total": float(e_ultra / e_total),
        "criterios": {
            "snr_min_db": snr_min_db,
            "max_diff_abs": max_diff_abs,
            "corr_min": 0.90,
        },
        "passou_snr": bool(passou_snr),
        "passou_max_diff": bool(passou_diff),
        "passou_correlacao": bool(passou_corr),
        "passou_inaudibilidade": bool(passou_snr and passou_diff and passou_corr),
        "nivel": _nivel_inaudibilidade(
            snr, max(corr, corr_spec), max_diff, corr_spec
        ),
    }
    return resultado


def resumo_validacao(resultado: Dict[str, Any]) -> str:
    """Texto legível do resultado da validação."""
    ok = resultado.get("passou_inaudibilidade", False)
    nivel = resultado.get("nivel", "?")
    linhas = [
        f"Inaudibilidade: {'PASSOU' if ok else 'ATENÇÃO'} (nível: {nivel})",
        f"  SNR (alinhado): {resultado.get('snr_db', 0):.1f} dB "
        f"[{'OK' if resultado.get('passou_snr') else 'BAIXO'}]",
        f"  Correlação temporal: {resultado.get('correlacao', 0):.4f} "
        f"[{'OK' if resultado.get('passou_correlacao') else 'BAIXA'}]",
        f"  Correlação espectral: {resultado.get('correlacao_espectral', 0):.4f}",
        f"  Max |diff|: {resultado.get('max_abs_diff', 0):.5f} "
        f"[{'OK' if resultado.get('passou_max_diff') else 'ALTA'}]",
        f"  Energia ultra na diff: {resultado.get('energia_diff_ultrassom', 0):.2e}",
    ]
    return "\n".join(linhas)


def estimar_impacto_asr(
    texto_original: Optional[str],
    texto_protegido: Optional[str],
) -> Dict[str, Any]:
    """
    Compara transcrições para evidenciar confusão do ASR.
    """
    o = (texto_original or "").strip().lower()
    p = (texto_protegido or "").strip().lower()
    if not o and not p:
        return {
            "comparavel": False,
            "motivo": "sem transcrições",
        }
    # Similaridade simples por tokens
    to, tp = set(o.split()), set(p.split())
    if not to and not tp:
        jaccard = 1.0
    else:
        jaccard = len(to & tp) / max(1, len(to | tp))
    iguais = o == p
    return {
        "comparavel": True,
        "textos_iguais": iguais,
        "jaccard_tokens": float(jaccard),
        "confundiu_asr": (not iguais) and jaccard < 0.85,
        "texto_original": o[:300],
        "texto_protegido": p[:300],
    }


def _nivel_inaudibilidade(
    snr: float, corr: float, max_diff: float, corr_spec: float = 0.0
) -> str:
    # All-pass reduz SNR temporal; espectro alto ainda indica boa invisibilidade
    if (snr >= 40 and corr >= 0.99) or corr_spec >= 0.995:
        return "excelente"
    if (snr >= 25 and corr >= 0.95) or corr_spec >= 0.98:
        return "boa"
    if (snr >= 15 and corr >= 0.90) or corr_spec >= 0.95:
        return "aceitável"
    return "audível_possivel"


def _energia_banda(
    y: np.ndarray, sr: int, f_lo: float, f_hi: float
) -> float:
    if f_lo >= f_hi or len(y) < 16:
        return 0.0
    n = int(2 ** np.floor(np.log2(min(len(y), 65536))))
    if n < 16:
        return 0.0
    windowed = y[:n] * np.hanning(n)
    spec = np.fft.rfft(windowed)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    return float(np.mean(np.abs(spec[mask]) ** 2)) if np.any(mask) else 0.0


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    n = min(len(x), len(y))
    if n < 8:
        return 1.0
    x0 = x[:n] - np.mean(x[:n])
    y0 = y[:n] - np.mean(y[:n])
    denom = np.sqrt(np.sum(x0**2) * np.sum(y0**2)) + 1e-12
    return float(np.sum(x0 * y0) / denom)


def _alinhar(
    a: np.ndarray, b: np.ndarray, max_lag: int = 512
) -> tuple:
    """Retorna (a_trim, b_trim, lag) com melhor correlação cruzada."""
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    max_lag = int(max(0, min(max_lag, n // 4)))
    if max_lag < 1:
        return a, b, 0

    # Decima para busca rápida de lag
    step = max(1, n // 6000)
    ad, bd = a[::step] - np.mean(a[::step]), b[::step] - np.mean(b[::step])
    lag_d = max(1, max_lag // step)

    best_lag = 0
    best = -1e18
    # lag > 0 => b atrasado
    for ld in range(-lag_d, lag_d + 1):
        if ld >= 0:
            x, y = ad[: len(ad) - ld], bd[ld:]
        else:
            x, y = ad[-ld:], bd[: len(bd) + ld]
        if len(x) < 16:
            continue
        score = float(np.dot(x, y))
        if score > best:
            best = score
            best_lag = int(ld * step)

    lag = int(np.clip(best_lag, -max_lag, max_lag))
    if lag >= 0:
        return a[: n - lag], b[lag:n], lag
    return a[-lag:n], b[: n + lag], lag


def _correlacao_espectral(a: np.ndarray, b: np.ndarray, sr: int) -> float:
    """Correlação das magnitudes médias do espectro (invisível se ~1)."""
    try:
        n = min(len(a), len(b), 16384)
        n = int(2 ** np.floor(np.log2(max(n, 512))))
        wa = np.hanning(n)
        fa = np.abs(np.fft.rfft(a[:n] * wa))
        fb = np.abs(np.fft.rfft(b[:n] * wa))
        # Banda audível principal
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        mask = (freqs >= 80.0) & (freqs <= min(12000.0, sr / 2 - 1))
        if not np.any(mask):
            mask = slice(None)
        return _pearson(fa[mask], fb[mask])
    except Exception:
        return 0.0


def _mono(audio: np.ndarray) -> np.ndarray:
    a = np.asarray(audio)
    if a.ndim == 2:
        a = np.mean(a, axis=0 if a.shape[0] <= 8 else 1)
    return a.flatten()
