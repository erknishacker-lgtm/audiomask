"""
GhostWave dual-layer (cloaker black → white).

VERDADE TÉCNICA (CapCut / TikTok legendas):
  Se a black está alta, clara e inteligível, o CapCut SEMPRE prefere legendar a black.
  Não existe truque open-source confiável de “humano ouve black e CapCut só ouve white”
  sem degradar a black. Quem promete 100% costuma mentir ou destruir o áudio.

O que fazemos de verdade:
  - modo "natural" (padrão): black 100% intacta + white residual baixíssima (watermark).
    Humano ouve perfeito. CapCut ainda legenda black — use para qualidade de anúncio.
  - modo "redirect" (experimental): mistura espectral na banda STT.
    Pode enganar ALGUNS sistemas fracos; CapCut costuma ainda acertar; áudio muda um pouco.
  - modo "white_only": arquivo só com a copy white (CapCut legenda white; humano também ouve white).

Use white_only quando o objetivo é “a legenda tem que ser a white”.
Use natural quando o objetivo é “o anúncio tem que soar bem”.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class CloakParams:
    """Parâmetros do cloaker."""

    # natural | redirect | white_only
    mode: str = "natural"
    # residual white time-domain (só natural/redirect)
    decoy_db: float = -40.0
    decoy_pre_emphasis: float = 0.5
    f_lo: float = 700.0
    f_hi: float = 3200.0
    n_fft: int = 1024
    hop: int = 256
    # só modo redirect
    stt_blend: float = 0.4
    black_scramble: float = 0.2
    env_smooth_s: float = 0.05
    floor: float = 0.05
    max_peak_ratio: float = 0.02
    seed: int = 7


def gerar_decoy_sintetico(
    texto: str,
    sr: int,
    duracao_s: Optional[float] = None,
    f0: float = 160.0,
) -> np.ndarray:
    """Fala sintética clara (formantes) para camada white."""
    chars = [c for c in texto.lower() if c.isalnum() or c == " "]
    if not chars:
        chars = list("oferta especial confira as condicoes oficiais no site")
    n_target = int((duracao_s or max(2.5, len(chars) * 0.075)) * sr)
    vogais = {
        "a": (800, 1200, 2500),
        "e": (500, 1700, 2500),
        "i": (300, 2200, 3000),
        "o": (500, 900, 2400),
        "u": (350, 700, 2300),
    }
    rng = np.random.default_rng(abs(hash(texto)) % (2**31))
    chunks = [np.zeros(int(0.04 * sr))]
    for ch in chars:
        n = max(1, int(0.07 * sr))
        if ch == " ":
            chunks.append(np.zeros(int(0.055 * sr)))
            continue
        forms = vogais.get(ch, (600, 1400, 2400))
        t = np.arange(n) / sr
        pitch = f0 * (1.0 + 0.04 * np.sin(2 * np.pi * 2.2 * t))
        phase = 2 * np.pi * np.cumsum(pitch) / sr
        source = 0.28 * np.sin(phase) + 0.03 * rng.standard_normal(n)
        env = np.ones(n)
        a, r = max(1, n // 10), max(1, n // 5)
        env[:a] = np.linspace(0, 1, a)
        env[-r:] = np.linspace(1, 0, r)
        sig = np.zeros(n)
        for i, f in enumerate(forms):
            sig += (1.0 / (i + 1)) * np.sin(2 * np.pi * f * t)
        sig = (0.8 * sig + 0.2 * source) * env
        chunks.append(sig)
    chunks.append(np.zeros(int(0.06 * sr)))
    y = np.concatenate(chunks).astype(np.float64)
    if len(y) < n_target:
        y = np.tile(y, int(np.ceil(n_target / len(y))))[:n_target]
    else:
        y = y[:n_target]
    y = bandpass(y, sr, 300.0, 3600.0)
    peak = np.max(np.abs(y)) + 1e-12
    return (0.9 * y / peak).astype(np.float32)


def alinhar_comprimento(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    n = max(len(a), len(b))
    aa, bb = np.zeros(n), np.zeros(n)
    aa[: len(a)] = a
    bb[: len(b)] = b
    return aa, bb


def envelope(y: np.ndarray, sr: int, smooth_s: float = 0.05) -> np.ndarray:
    env = np.abs(y.astype(np.float64))
    win = max(1, int(smooth_s * sr))
    env = np.convolve(env, np.ones(win) / win, mode="same")
    return env / (float(np.max(env)) + 1e-12)


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


def _inject_quiet_white(
    main: np.ndarray, white: np.ndarray, sr: int, p: CloakParams
) -> np.ndarray:
    """White residual baixíssima sob mascaramento — não altera perceptivelmente a black."""
    dec = bandpass(white, sr, 300.0, 3600.0)
    dec = pre_emphasis(dec) * 0.5 + dec * 0.5
    env = envelope(main, sr, p.env_smooth_s)
    # white só sobe um pouco em silêncio (ainda limitada)
    gate = np.clip(p.floor + (1.0 - env) * 0.3, 0.02, 0.5)
    rms_m = float(np.sqrt(np.mean(main**2)) + 1e-12)
    rms_d = float(np.sqrt(np.mean(dec**2)) + 1e-12)
    g = (rms_m * (10.0 ** (p.decoy_db / 20.0))) / rms_d
    white_t = dec * gate * g
    peak_m = float(np.max(np.abs(main)) + 1e-12)
    peak_w = float(np.max(np.abs(white_t)) + 1e-12)
    cap = peak_m * p.max_peak_ratio
    if peak_w > cap:
        white_t *= cap / peak_w
    out = main + white_t
    peak = float(np.max(np.abs(out)) + 1e-12)
    if peak > 0.99:
        out *= 0.99 / peak
    return out


def _stft_redirect(
    main: np.ndarray,
    white: np.ndarray,
    sr: int,
    p: CloakParams,
    rng: np.random.Generator,
) -> np.ndarray:
    """Redirect experimental — pode piorar áudio; CapCut ainda pode acertar black."""
    n_fft, hop = p.n_fft, p.hop
    n = len(main)
    if n < n_fft:
        return _inject_quiet_white(main, white, sr, p)

    window = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
    mask = (freqs >= p.f_lo) & (freqs <= p.f_hi)
    out = np.zeros(n)
    norm = np.zeros(n)
    blend = float(np.clip(p.stt_blend, 0.15, 0.55))
    scramble = float(np.clip(p.black_scramble, 0.0, 0.4))

    for start in range(0, n - n_fft + 1, hop):
        fb = main[start : start + n_fft] * window
        fw = white[start : start + n_fft] * window
        sb, sw = np.fft.rfft(fb), np.fft.rfft(fw)
        mb, pb = np.abs(sb), np.angle(sb)
        mw, pw = np.abs(sw), np.angle(sw)
        e_b = float(np.mean(mb[mask]) + 1e-12)
        e_w = float(np.mean(mw[mask]) + 1e-12)
        mw_s = mw * (e_b / e_w)
        mb2, pb2 = mb.copy(), pb.copy()
        if scramble > 0:
            pb2[mask] = pb[mask] + rng.uniform(-np.pi, np.pi, size=pb.shape)[mask] * scramble
            mb2[mask] *= 1.0 - 0.15 * scramble
        mb2[mask] = (1.0 - blend) * mb2[mask] + blend * mw_s[mask]
        pb2[mask] = (1.0 - blend * 0.5) * pb2[mask] + (blend * 0.5) * pw[mask]
        recon = np.fft.irfft(mb2 * np.exp(1j * pb2), n=n_fft).real
        out[start : start + n_fft] += recon * window
        norm[start : start + n_fft] += window**2

    norm = np.maximum(norm, 1e-8)
    y = out / norm
    y = np.where(norm < 1e-3, main, y)
    # Casa loudness com black
    rms_m = float(np.sqrt(np.mean(main**2)) + 1e-12)
    rms_y = float(np.sqrt(np.mean(y**2)) + 1e-12)
    y *= rms_m / rms_y
    return y


def aplicar_cloaker(
    principal: np.ndarray,
    decoy: np.ndarray,
    sr: int,
    params: Optional[CloakParams] = None,
) -> Tuple[np.ndarray, dict]:
    p = params or CloakParams()
    mode = (p.mode or "natural").lower().strip()
    main = _mono(principal).astype(np.float64)
    dec = _mono(decoy).astype(np.float64)
    main, dec = alinhar_comprimento(main, dec)
    rng = np.random.default_rng(p.seed)

    if mode == "white_only":
        # CapCut VAI legendar a white — e o humano também ouve a white
        out = dec / (np.max(np.abs(dec)) + 1e-12)
        peak_m = float(np.max(np.abs(main)) + 1e-12)
        out = out * peak_m * 0.9
        meta = {
            "cloaker": True,
            "engine": "white_only",
            "mode": mode,
            "corr_vs_black": float(np.corrcoef(main, out)[0, 1]) if len(main) > 8 else 0.0,
            "human_hears": "white",
            "capcut_likely_hears": "white",
            "nota": "Modo white_only: legenda e ouvido humanos seguem a copy white.",
        }
        return np.clip(out, -1, 1).astype(np.float32), meta

    if mode == "redirect":
        y = _stft_redirect(main, dec, sr, p, rng)
        y = _inject_quiet_white(y, dec, sr, p)
        corr = float(np.corrcoef(main, y)[0, 1]) if len(main) > 8 else 1.0
        meta = {
            "cloaker": True,
            "engine": "stt_redirect_spectral",
            "mode": mode,
            "stt_blend": p.stt_blend,
            "corr_vs_black": corr,
            "human_hears": "mostly_black",
            "capcut_likely_hears": "often_still_black",
            "nota": (
                "Redirect experimental. CapCut moderno costuma AINDA legendar a black. "
                "Se a legenda precisa ser white, use mode=white_only."
            ),
        }
        peak = float(np.max(np.abs(y)) + 1e-12)
        if peak > 0.99:
            y *= 0.99 / peak
        return y.astype(np.float32), meta

    # natural (padrão): black 100% + white residual imperceptível
    y = _inject_quiet_white(main, dec, sr, p)
    corr = float(np.corrcoef(main, y)[0, 1]) if len(main) > 8 else 1.0
    meta = {
        "cloaker": True,
        "engine": "natural_black_plus_quiet_white",
        "mode": "natural",
        "decoy_db": p.decoy_db,
        "corr_vs_black": corr,
        "human_hears": "black",
        "capcut_likely_hears": "black",
        "nota": (
            "Áudio black preservado (qualidade de anúncio). "
            "CapCut/TikTok VÃO legendar a black se ela for fala clara — "
            "isso é normal. Para forçar legenda white, use white_only."
        ),
    }
    return y.astype(np.float32), meta


def _mono(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a)
    if x.ndim == 1:
        return x
    if x.ndim == 2:
        if x.shape[0] <= 8 and x.shape[0] < x.shape[1]:
            return np.mean(x, axis=0)
        return np.mean(x, axis=1)
    return x.flatten()
