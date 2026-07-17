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
