"""
Cloaker black → white (dual-copy).

- Trilha PRINCIPAL (black): fica 100% audível e natural para humanos.
- Trilha DECOY (white): copy “limpa” em volume baixo, moldada para ASR
  (banda da fala + envelope), com mascaramento psicoacústico.

A IA de legenda costuma se prender a trechos “fáceis” de transcrever;
a white copy é limpa e contínua. A black permanece alta e natural.

Não é garantia 100% em todos os ASRs — é o melhor desenho prático
para “humano ouve black / máquina tende a white”.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class CloakParams:
    """Parâmetros do cloaker."""

    # Nível white vs principal. Um pouco mais alto que -24 para STT "pegar" a white
    # sem poluir o black (humano ainda ouve black dominante).
    decoy_db: float = -20.0
    # Reforço da white na banda ASR (pré-ênfase)
    decoy_pre_emphasis: float = 0.55
    # Banda da fala — STT prioriza
    f_lo: float = 300.0
    f_hi: float = 3400.0
    env_smooth_s: float = 0.04
    # Em silêncios da black, white sobe (STT prefere trechos limpos)
    floor: float = 0.22
    # Pico extra da white só em gaps da black
    gap_boost: float = 1.8
    seed: int = 7


def gerar_decoy_sintetico(
    texto: str,
    sr: int,
    duracao_s: Optional[float] = None,
    f0: float = 155.0,
) -> np.ndarray:
    """
    Gera fala sintética “white” (formantes claros) — fácil para ASR.
    Se não houver áudio white do usuário, usa isso.
    """
    # Duração por caractere
    chars = [c for c in texto.lower() if c.isalnum() or c == " "]
    if not chars:
        chars = list("oferta especial confira as condicoes")
    n_target = int((duracao_s or max(2.0, len(chars) * 0.07)) * sr)
    vogais = {
        "a": (800, 1200, 2500),
        "e": (500, 1700, 2500),
        "i": (300, 2200, 3000),
        "o": (500, 900, 2400),
        "u": (350, 700, 2300),
    }
    rng = np.random.default_rng(abs(hash(texto)) % (2**31))
    chunks = [np.zeros(int(0.05 * sr))]
    for ch in chars:
        n = max(1, int(0.065 * sr))
        if ch == " ":
            chunks.append(np.zeros(int(0.05 * sr)))
            continue
        forms = vogais.get(ch, (600, 1400, 2400))
        t = np.arange(n) / sr
        pitch = f0 * (1.0 + 0.03 * np.sin(2 * np.pi * 2.5 * t))
        phase = 2 * np.pi * np.cumsum(pitch) / sr
        source = 0.25 * np.sin(phase) + 0.04 * rng.standard_normal(n)
        env = np.ones(n)
        a, r = max(1, n // 12), max(1, n // 6)
        env[:a] = np.linspace(0, 1, a)
        env[-r:] = np.linspace(1, 0, r)
        sig = np.zeros(n)
        for i, f in enumerate(forms):
            sig += (1.0 / (i + 1)) * np.sin(2 * np.pi * f * t)
        sig = (0.75 * sig + 0.25 * source) * env
        chunks.append(sig)
    chunks.append(np.zeros(int(0.08 * sr)))
    y = np.concatenate(chunks).astype(np.float64)
    # Ajusta duração
    if len(y) < n_target:
        # repete loop suave
        reps = int(np.ceil(n_target / len(y)))
        y = np.tile(y, reps)[:n_target]
    else:
        y = y[:n_target]
    peak = np.max(np.abs(y)) + 1e-12
    return (0.85 * y / peak).astype(np.float32)


def alinhar_comprimento(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    n = max(len(a), len(b))
    aa = np.zeros(n, dtype=np.float64)
    bb = np.zeros(n, dtype=np.float64)
    aa[: len(a)] = a
    bb[: len(b)] = b
    return aa, bb


def envelope(y: np.ndarray, sr: int, smooth_s: float = 0.05) -> np.ndarray:
    env = np.abs(y.astype(np.float64))
    win = max(1, int(smooth_s * sr))
    kernel = np.ones(win) / win
    env = np.convolve(env, kernel, mode="same")
    m = float(np.max(env)) + 1e-12
    return env / m


def bandpass(x: np.ndarray, sr: int, f_lo: float, f_hi: float) -> np.ndarray:
    try:
        from scipy.signal import butter, sosfiltfilt

        nyq = sr / 2.0
        lo = max(f_lo / nyq, 0.001)
        hi = min(f_hi / nyq, 0.99)
        if lo >= hi:
            return x
        sos = butter(4, [lo, hi], btype="band", output="sos")
        return sosfiltfilt(sos, x)
    except Exception:
        return x


def pre_emphasis(x: np.ndarray, coef: float = 0.97) -> np.ndarray:
    y = np.copy(x)
    y[1:] = x[1:] - coef * x[:-1]
    return y


def aplicar_cloaker(
    principal: np.ndarray,
    decoy: np.ndarray,
    sr: int,
    params: Optional[CloakParams] = None,
) -> Tuple[np.ndarray, dict]:
    """
    Mix final: principal (black) intacta em nível + decoy (white) baixo e mascarado.

    Returns:
        mono float32, metadados
    """
    p = params or CloakParams()
    main = _mono(principal).astype(np.float64)
    dec = _mono(decoy).astype(np.float64)
    main, dec = alinhar_comprimento(main, dec)

    # White: limpa, banda da fala, pré-ênfase (ASR gosta)
    dec = bandpass(dec, sr, p.f_lo, p.f_hi)
    if p.decoy_pre_emphasis > 0:
        dec = (1.0 - p.decoy_pre_emphasis) * dec + p.decoy_pre_emphasis * pre_emphasis(
            dec
        )

    # Envelope da principal: onde black é forte, white se esconde;
    # onde black silencia, white sobe (melhor para STT ouvir a white).
    env_main = envelope(main, sr, p.env_smooth_s)
    inv = 1.0 - env_main
    gate = np.clip(p.floor + inv * (p.gap_boost - p.floor), 0.05, 2.5)

    rms_m = float(np.sqrt(np.mean(main**2)) + 1e-12)
    rms_d = float(np.sqrt(np.mean(dec**2)) + 1e-12)
    ganho = (rms_m * (10.0 ** (p.decoy_db / 20.0))) / rms_d
    white = dec * gate * ganho

    # BLACK intocado em nível — só soma white mascarada
    out = main + white
    peak = float(np.max(np.abs(out)) + 1e-12)
    if peak > 0.99:
        out = out * (0.99 / peak)

    meta = {
        "cloaker": True,
        "engine": "dual_layer_ghostwave",
        "decoy_db": p.decoy_db,
        "rms_main": rms_m,
        "rms_white": float(np.sqrt(np.mean(white**2))),
        "snr_white_vs_main_db": float(
            10 * np.log10((rms_m**2) / (float(np.mean(white**2)) + 1e-12))
        ),
        "human_layer": "original_black_preserved",
        "ai_layer": "white_transcript_injected",
    }
    return out.astype(np.float32), meta


def _mono(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a)
    if x.ndim == 1:
        return x
    if x.ndim == 2:
        if x.shape[0] <= 8 and x.shape[0] < x.shape[1]:
            return np.mean(x, axis=0)
        return np.mean(x, axis=1)
    return x.flatten()
