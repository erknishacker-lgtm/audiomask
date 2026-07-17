"""
GhostWave dual-layer (estilo MaskAI):

- HUMAN LAYER (black): o criativo original — o ouvido humano continua
  ouvindo a mensagem black de forma natural.
- AI LAYER (white): copy limpa injetada na BANDA que o STT prioriza
  (≈800–3000 Hz), via STFT, para a legenda automática tender a ler a white.

Importante:
  Só somar white a -36 dB NÃO redireciona CapCut — o ASR segue a black alta.
  Aqui a white SUBSTITUI parte da energia espectral na faixa do STT, e a black
  é levemente “embaçada” só nessa faixa (fase/mag), sem destruir a voz.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class CloakParams:
    """Parâmetros do dual-layer STT-redirect."""

    # Fração da banda STT vinda da white (0.35–0.65). Maior = mais redirect, mais artefato.
    stt_blend: float = 0.52
    # Embaralha um pouco a black na banda STT (dificulta ASR na black)
    black_scramble: float = 0.35
    # Nível residual time-domain da white (baixo)
    decoy_db: float = -32.0
    decoy_pre_emphasis: float = 0.7
    # Banda onde STT/CapCut “olha” mais
    f_lo: float = 700.0
    f_hi: float = 3200.0
    n_fft: int = 1024
    hop: int = 256
    env_smooth_s: float = 0.05
    floor: float = 0.06
    seed: int = 7


def gerar_decoy_sintetico(
    texto: str,
    sr: int,
    duracao_s: Optional[float] = None,
    f0: float = 160.0,
) -> np.ndarray:
    """Fala sintética clara (formantes) — fácil para ASR."""
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
            sig += (1.0 / (i + 1)) * np.sin(2 * np.pi * f * t + rng.uniform(0, 0.5))
        sig = (0.8 * sig + 0.2 * source) * env
        chunks.append(sig)
    chunks.append(np.zeros(int(0.06 * sr)))
    y = np.concatenate(chunks).astype(np.float64)
    if len(y) < n_target:
        y = np.tile(y, int(np.ceil(n_target / len(y))))[:n_target]
    else:
        y = y[:n_target]
    # Fala white bem limpa e “quente” no mid (bom para STT)
    y = bandpass(y, sr, 300.0, 3600.0)
    peak = np.max(np.abs(y)) + 1e-12
    return (0.9 * y / peak).astype(np.float32)


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


def _stft_dual(
    main: np.ndarray,
    white: np.ndarray,
    sr: int,
    p: CloakParams,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Dual-layer espectral:
    - fora da banda STT: black 100%
    - na banda STT: mistura mag white + embaraça black
    """
    n_fft, hop = p.n_fft, p.hop
    n = len(main)
    if n < n_fft:
        return main + 0.05 * white

    window = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
    mask = (freqs >= p.f_lo) & (freqs <= p.f_hi)

    out = np.zeros(n)
    norm = np.zeros(n)
    blend = float(np.clip(p.stt_blend, 0.15, 0.75))
    scramble = float(np.clip(p.black_scramble, 0.0, 0.8))

    for start in range(0, n - n_fft + 1, hop):
        fb = main[start : start + n_fft] * window
        fw = white[start : start + n_fft] * window
        sb = np.fft.rfft(fb)
        sw = np.fft.rfft(fw)
        mb, pb = np.abs(sb), np.angle(sb)
        mw, pw = np.abs(sw), np.angle(sw)

        # Escala white para energia similar na banda
        e_b = float(np.mean(mb[mask]) + 1e-12)
        e_w = float(np.mean(mw[mask]) + 1e-12)
        mw_s = mw * (e_b / e_w)

        mb2 = mb.copy()
        pb2 = pb.copy()

        # Embaralha black na banda (ASR da black piora; humano ainda entende)
        if scramble > 0:
            jitter = rng.uniform(-np.pi, np.pi, size=pb.shape) * scramble
            pb2[mask] = pb[mask] + jitter[mask]
            # Atenua um pouco formantes da black na banda STT
            mb2[mask] = mb2[mask] * (1.0 - 0.25 * scramble)

        # Injeta white: mag misturada + fase puxada para white (STT gosta)
        mb2[mask] = (1.0 - blend) * mb2[mask] + blend * mw_s[mask]
        # Fase: blend black embaralhada com white
        pb2[mask] = (1.0 - blend * 0.85) * pb2[mask] + (blend * 0.85) * pw[mask]

        recon = np.fft.irfft(mb2 * np.exp(1j * pb2), n=n_fft).real
        out[start : start + n_fft] += recon * window
        norm[start : start + n_fft] += window**2

    norm = np.maximum(norm, 1e-8)
    y = out / norm
    # Cola bordas
    if np.any(norm < 1e-3):
        y = np.where(norm < 1e-3, main, y)
    return y


def aplicar_cloaker(
    principal: np.ndarray,
    decoy: np.ndarray,
    sr: int,
    params: Optional[CloakParams] = None,
) -> Tuple[np.ndarray, dict]:
    """
    Dual-layer STT-redirect (humano ≈ black; STT tende white).
    """
    p = params or CloakParams()
    rng = np.random.default_rng(p.seed)
    main = _mono(principal).astype(np.float64)
    dec = _mono(decoy).astype(np.float64)
    main, dec = alinhar_comprimento(main, dec)

    # White limpa para ASR
    dec = bandpass(dec, sr, 250.0, 3800.0)
    if p.decoy_pre_emphasis > 0:
        pe = pre_emphasis(dec)
        dec = (1.0 - p.decoy_pre_emphasis) * dec + p.decoy_pre_emphasis * pe
    # Normaliza white
    dec = dec / (np.max(np.abs(dec)) + 1e-12) * (np.max(np.abs(main)) + 1e-12) * 0.85

    # Camada espectral (coração do redirect)
    y = _stft_dual(main, dec, sr, p, rng)

    # Residual time-domain bem baixo (preenche gaps, não “grita”)
    env = envelope(main, sr, p.env_smooth_s)
    gate = np.maximum(1.0 - env, p.floor)
    rms_m = float(np.sqrt(np.mean(main**2)) + 1e-12)
    rms_d = float(np.sqrt(np.mean(dec**2)) + 1e-12)
    g = (rms_m * (10.0 ** (p.decoy_db / 20.0))) / rms_d
    residual = dec * gate * g
    y = y + residual

    # Casa energia com o original (preserva loudness black)
    rms_y = float(np.sqrt(np.mean(y**2)) + 1e-12)
    y = y * (rms_m / rms_y)
    peak = float(np.max(np.abs(y)) + 1e-12)
    if peak > 0.99:
        y *= 0.99 / peak

    corr = float(np.corrcoef(main, y)[0, 1]) if len(main) > 8 else 1.0
    meta = {
        "cloaker": True,
        "engine": "stt_redirect_spectral",
        "stt_blend": p.stt_blend,
        "black_scramble": p.black_scramble,
        "decoy_db_residual": p.decoy_db,
        "band_hz": [p.f_lo, p.f_hi],
        "corr_vs_black": corr,
        "human_layer": "black_intelligible",
        "ai_layer": "white_stt_band_injection",
        "nota": (
            "Dual-layer espectral: banda STT recebe white; black permanece "
            "inteligível. CapCut/TikTok não garantem 0% black — teste sempre."
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
