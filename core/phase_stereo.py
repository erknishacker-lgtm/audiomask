"""
Encriptamento phase-stereo “invisível”.

Codifica informação auxiliar em diferença L/R (side) com nível baixo.
- Em mono (muitos players/ASR downmix): side se cancela parcialmente.
- Em stereo: imperceptível se o side for baixo e correlacionado.

Uso: proteção / watermark + reforço da white copy no side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class PhaseStereoParams:
    side_db: float = -38.0  # side bem abaixo do limiar perceptivo
    invert_side: bool = True
    seed: int = 11


def mono_para_stereo_protegido(
    mono: np.ndarray,
    payload: Optional[np.ndarray] = None,
    sr: int = 48000,
    params: Optional[PhaseStereoParams] = None,
) -> Tuple[np.ndarray, dict]:
    """
    Converte mono → stereo (2, N) com side invisível.

    Args:
        mono: sinal principal (black+white já mixados ou só black)
        payload: opcional (ex.: white copy) injetado no side
    """
    p = params or PhaseStereoParams()
    m = _mono(mono).astype(np.float64)
    n = len(m)

    if payload is not None:
        side = _mono(payload).astype(np.float64)
        if len(side) < n:
            side = np.pad(side, (0, n - len(side)))
        else:
            side = side[:n]
    else:
        rng = np.random.default_rng(p.seed)
        # payload pseudo-aleatório banda estreita (watermark)
        side = rng.standard_normal(n)
        try:
            from scipy.signal import butter, sosfiltfilt

            nyq = sr / 2.0
            sos = butter(3, [300 / nyq, 3400 / nyq], btype="band", output="sos")
            side = sosfiltfilt(sos, side)
        except Exception:
            pass

    rms_m = float(np.sqrt(np.mean(m**2)) + 1e-12)
    rms_s = float(np.sqrt(np.mean(side**2)) + 1e-12)
    g = (rms_m * (10.0 ** (p.side_db / 20.0))) / rms_s
    side = side * g
    if p.invert_side:
        # L = mid+side, R = mid-side  (mid = mono)
        left = m + side
        right = m - side
    else:
        left = m + side
        right = m + 0.5 * side

    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-12)
    if peak > 0.99:
        left *= 0.99 / peak
        right *= 0.99 / peak

    stereo = np.stack([left, right], axis=0).astype(np.float32)
    meta = {
        "phase_stereo": True,
        "side_db": p.side_db,
        "shape": list(stereo.shape),
    }
    return stereo, meta


def _mono(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a)
    if x.ndim == 1:
        return x
    if x.ndim == 2:
        if x.shape[0] <= 8 and x.shape[0] < x.shape[1]:
            return np.mean(x, axis=0)
        return np.mean(x, axis=1)
    return x.flatten()


def encode_mid_side_cloak(
    black: np.ndarray,
    white: np.ndarray,
    sr: int = 48000,
    white_db: float = -22.0,
) -> Tuple[np.ndarray, dict]:
    """
    Codificação do mercado (arquivo *_shielded.mp4 analisado):

      L ≈ black + white_scaled
      R ≈ -black + white_scaled

    ⇒ mid (L+R)/2 ≈ white   ← o que o TikTok costuma ouvir no mono
    ⇒ side (L-R)/2 ≈ black  ← o que o humano ouve no estéreo

    white_db: nível da secondary vs black (ref. pago ≈ −20…−22 dB).
    """
    b = _mono(black).astype(np.float64)
    w = _mono(white).astype(np.float64)
    n = max(len(b), len(w))
    if len(b) < n:
        b = np.pad(b, (0, n - len(b)))
    else:
        b = b[:n]
    if len(w) < n:
        w = np.pad(w, (0, n - len(w)))
    else:
        w = w[:n]

    # bandpass leve na white (voz)
    try:
        from scipy.signal import butter, sosfiltfilt

        nyq = sr / 2.0
        sos = butter(3, [120 / nyq, min(0.99, 6500 / nyq)], btype="band", output="sos")
        w = sosfiltfilt(sos, w)
    except Exception:
        pass

    rms_b = float(np.sqrt(np.mean(b**2)) + 1e-12)
    rms_w = float(np.sqrt(np.mean(w**2)) + 1e-12)
    # white_db relativo à black (ex.: -22)
    target = rms_b * (10.0 ** (float(white_db) / 20.0))
    w_s = w * (target / rms_w)

    left = b + w_s
    right = -b + w_s

    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-12)
    if peak > 0.99:
        left *= 0.99 / peak
        right *= 0.99 / peak
        w_s *= 0.99 / peak
        b_out = b * (0.99 / peak)
    else:
        b_out = b

    stereo = np.stack([left, right], axis=0).astype(np.float32)
    mid = (left + right) / 2.0
    side = (left - right) / 2.0
    rms_mid = float(np.sqrt(np.mean(mid**2)) + 1e-12)
    rms_side = float(np.sqrt(np.mean(side**2)) + 1e-12)
    meta = {
        "phase_stereo": True,
        "engine": "mid_side_invert_cloak",
        "white_db": float(white_db),
        "mid_vs_side_db": float(20.0 * np.log10(rms_mid / rms_side + 1e-20)),
        "corr_L_vs_minus_R": float(np.corrcoef(left, -right)[0, 1]) if n > 8 else 0.0,
        "shape": list(stereo.shape),
        "human_stereo": "black_on_side",
        "mono_downmix": "white_on_mid",
        "nota": (
            "Estéreo invertido estilo mercado: mono/TikTok tende a ouvir a white; "
            "fone estéreo ouve a black."
        ),
    }
    return stereo, meta
