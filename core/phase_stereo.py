"""
Encriptamento phase-stereo "invisível".

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
    white: Optional[np.ndarray] = None,
    sr: int = 48000,
    white_db: float = -22.0,
) -> Tuple[np.ndarray, dict]:
    """
    Codificação de inversão de fase (análise de mercado *_shielded.mp4):

    Modo puro (white=None, padrão):
      L = black
      R = -black
      ⇒ mono (L+R)/2 ≈ 0  — silêncio: TikTok não detecta nada → APROVADO
      ⇒ side (L-R)/2 = black — fone estéreo ouve o conteúdo completo

    Modo com white (white_db controla o nível da white no mid):
      L = black + white_scaled
      R = -black + white_scaled
      ⇒ mid = white_scaled, side = black
    """
    b = _mono(black).astype(np.float64)

    # Modo puro: inversão de fase sem white no mono (igual à referência analisada)
    if white is None:
        peak_b = float(np.max(np.abs(b)) + 1e-12)
        if peak_b > 0.99:
            b = b * (0.99 / peak_b)
        left = b
        right = -b
        stereo = np.stack([left, right], axis=0).astype(np.float32)
        mid = (left + right) / 2.0
        side = (left - right) / 2.0
        rms_mid = float(np.sqrt(np.mean(mid**2)) + 1e-12)
        rms_side = float(np.sqrt(np.mean(side**2)) + 1e-12)
        return stereo, {
            "phase_stereo": True,
            "engine": "pure_anti_phase_cloak",
            "white_db": None,
            "mid_vs_side_db": float(20.0 * np.log10(rms_mid / rms_side + 1e-20)),
            "corr_L_vs_minus_R": float(np.corrcoef(left, -right)[0, 1]) if len(left) > 8 else 0.0,
            "shape": list(stereo.shape),
            "channels": 2,
            "human_stereo": "black_on_side",
            "mono_downmix": "silence",
            "quality_ok": True,
            "nota": "Inversão pura L=-R: mono ≈ silêncio. TikTok não detecta conteúdo → aprovado.",
        }

    w = _mono(white).astype(np.float64)
    n = max(len(b), len(w))
    if len(b) < n:
        b = np.pad(b, (0, n - len(b)))
    else:
        b = b[:n]
    if len(w) < n:
        # repete a fala white (com gap) para cobrir o anúncio inteiro
        if len(w) > sr // 4:
            gap = np.zeros(int(0.15 * sr), dtype=np.float64)
            parts = [w]
            cur = len(w)
            while cur < n:
                parts.append(gap)
                parts.append(w)
                cur += len(gap) + len(w)
            w = np.concatenate(parts)[:n]
        else:
            w = np.pad(w, (0, n - len(w)))
    else:
        w = w[:n]

    # banda de voz — copy TTS inteligível no mono
    try:
        from scipy.signal import butter, sosfiltfilt

        nyq = sr / 2.0
        sos = butter(3, [90 / nyq, min(0.99, 7200 / nyq)], btype="band", output="sos")
        w = sosfiltfilt(sos, w)
    except Exception:
        pass

    # normaliza black para headroom (evita clip que desbalanceia L/R)
    peak_b = float(np.max(np.abs(b)) + 1e-12)
    if peak_b > 0.92:
        b = b * (0.92 / peak_b)

    rms_b = float(np.sqrt(np.mean(b**2)) + 1e-12)
    rms_w = float(np.sqrt(np.mean(w**2)) + 1e-12)
    w_db = float(white_db)
    if w_db < -36.0:
        w_db = -22.0
    if w_db > -18.0:
        w_db = -20.0
    target = rms_b * (10.0 ** (w_db / 20.0))
    w_s = w * (target / max(rms_w, 1e-12))

    # Truque exato: black em oposição de fase; white em fase
    left = b + w_s
    right = -b + w_s

    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-12)
    if peak > 0.99:
        scale = 0.99 / peak
        left *= scale
        right *= scale
        w_s *= scale
        b *= scale

    stereo = np.stack([left, right], axis=0).astype(np.float32)
    mid = (left + right) / 2.0  # == white_scaled
    side = (left - right) / 2.0  # == black
    rms_mid = float(np.sqrt(np.mean(mid**2)) + 1e-12)
    rms_side = float(np.sqrt(np.mean(side**2)) + 1e-12)

    # qualidade do cancelamento (quanto de black vaza no mono)
    def _corr(a: np.ndarray, c: np.ndarray) -> float:
        a = np.asarray(a, dtype=np.float64).flatten()
        c = np.asarray(c, dtype=np.float64).flatten()
        nn = min(len(a), len(c))
        a, c = a[:nn], c[:nn]
        a = a - a.mean()
        c = c - c.mean()
        den = float(np.linalg.norm(a) * np.linalg.norm(c) + 1e-12)
        return float(np.dot(a, c) / den)

    corr_mid_white = _corr(mid, w_s)
    corr_mid_black = _corr(mid, b)
    corr_side_black = _corr(side, b)
    meta = {
        "phase_stereo": True,
        "engine": "mid_side_invert_cloak",
        "white_db": float(w_db),
        "mid_vs_side_db": float(20.0 * np.log10(rms_mid / rms_side + 1e-20)),
        "corr_L_vs_minus_R": float(np.corrcoef(left, -right)[0, 1]) if n > 8 else 0.0,
        "corr_mono_vs_white": corr_mid_white,
        "corr_mono_vs_black": corr_mid_black,
        "corr_side_vs_black": corr_side_black,
        "shape": list(stereo.shape),
        "channels": 2,
        "human_stereo": "black_on_side_white_quiet_center",
        "mono_downmix": "white_only",
        "quality_ok": bool(
            corr_mid_white > 0.9
            and abs(corr_mid_black) < 0.15
            and corr_side_black > 0.9
        ),
        "nota": (
            "Estéreo mid-side: fone estéreo → anúncio (black). "
            "Mono/TikTok → copy white limpa. White é fala TTS, não ruído."
        ),
    }
    return stereo, meta


def mono_downmix_from_stereo(stereo: np.ndarray) -> np.ndarray:
    """(L+R)/2 — o que o TikTok costuma ouvir."""
    x = np.asarray(stereo, dtype=np.float32)
    if x.ndim == 1:
        return x
    if x.shape[0] == 2 and x.shape[0] < x.shape[1]:
        return (0.5 * (x[0] + x[1])).astype(np.float32)
    if x.shape[1] == 2:
        return (0.5 * (x[:, 0] + x[:, 1])).astype(np.float32)
    return _mono(x).astype(np.float32)
