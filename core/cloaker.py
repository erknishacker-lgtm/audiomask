"""
GhostWave dual-layer (cloaker black → white).

VERDADE TÉCNICA:
  Se a black está alta, clara e inteligível, extratores de fala (STT/ASR de ads)
  tendem a ler a black. Não existe truque open-source confiável de
  “humano ouve black e a IA só ouve white” sem degradar a black.

Modos:
  - natural: black 100% + white residual baixíssima (watermark). Som perfeito.
  - anti_analise: black principal + white dinâmica sob mascaramento + micro-scramble
    leve na banda de voz. Mira robô de análise de ads (proxy Whisper), não legenda 100%.
  - redirect: mistura espectral experimental na banda STT (pode alterar o áudio).
  - white_only: só white (legenda e ouvido humanos seguem white).

Use natural para qualidade máxima.
Use anti_analise para tentar sujar a leitura da black sem estragar o anúncio.
Use white_only quando o objetivo é a white ser o que se ouve/legenda.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class CloakParams:
    """Parâmetros do cloaker."""

    # natural | anti_analise | redirect | white_only
    mode: str = "natural"
    # residual white time-domain
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
    # anti_analise: white sob picos da fala + micro-scramble de fase
    micro_scramble: float = 0.12
    mask_under_speech: float = 0.85  # 0..1 quanto a white sobe com o envelope da black


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


def _inject_masked_white(
    main: np.ndarray, white: np.ndarray, sr: int, p: CloakParams
) -> np.ndarray:
    """
    White dinâmica sob a fala (mascaramento psicoacústico simples).

    Diferente do residual natural: a white sobe JUNTO com o envelope da black
    (onde o ouvido mascara melhor), ~-28..-32 dB RMS relativo — ainda quieta,
    porém mais presente para extratores de fala do que -40 dB fixo.
    """
    dec = bandpass(white, sr, 280.0, 3800.0)
    dec = pre_emphasis(dec, 0.85) * float(p.decoy_pre_emphasis) + dec * (
        1.0 - float(p.decoy_pre_emphasis)
    )
    env = envelope(main, sr, p.env_smooth_s)
    under = float(np.clip(p.mask_under_speech, 0.0, 1.0))
    # gate alto sob fala (env), baixo no silêncio — evita white “sussurro solto”
    gate = np.clip(p.floor + under * env + (1.0 - under) * 0.15, 0.04, 1.0)
    rms_m = float(np.sqrt(np.mean(main**2)) + 1e-12)
    rms_d = float(np.sqrt(np.mean(dec**2)) + 1e-12)
    decoy = float(p.decoy_db)
    # anti_analise padrão: um degrau acima do natural (-40)
    if decoy <= -38.0:
        decoy = -30.0
    g = (rms_m * (10.0 ** (decoy / 20.0))) / rms_d
    white_t = dec * gate * g
    peak_m = float(np.max(np.abs(main)) + 1e-12)
    # permite picos um pouco maiores que natural (ainda << black)
    cap_ratio = max(float(p.max_peak_ratio), 0.06)
    peak_w = float(np.max(np.abs(white_t)) + 1e-12)
    cap = peak_m * cap_ratio
    if peak_w > cap:
        white_t *= cap / peak_w
    out = main + white_t
    peak = float(np.max(np.abs(out)) + 1e-12)
    if peak > 0.99:
        out *= 0.99 / peak
    return out


def _micro_scramble_stt_band(
    main: np.ndarray,
    sr: int,
    p: CloakParams,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Micro-perturbação de fase na banda de voz (~700–3200 Hz).
    Leve o bastante para anúncio; pode sujar ASR/embeddings.
    """
    scramble = float(np.clip(p.micro_scramble, 0.0, 0.28))
    if scramble <= 1e-6:
        return main
    n_fft, hop = p.n_fft, p.hop
    n = len(main)
    if n < n_fft:
        return main
    window = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
    mask = (freqs >= p.f_lo) & (freqs <= p.f_hi)
    out = np.zeros(n)
    norm = np.zeros(n)
    for start in range(0, n - n_fft + 1, hop):
        frame = main[start : start + n_fft] * window
        s = np.fft.rfft(frame)
        mag, ph = np.abs(s), np.angle(s)
        ph2 = ph.copy()
        ph2[mask] = ph[mask] + rng.uniform(-np.pi, np.pi, size=ph.shape)[mask] * scramble
        # leve atenuação aleatória de magnitude na banda (muito sutil)
        mag2 = mag.copy()
        mag2[mask] *= 1.0 - 0.08 * scramble * rng.random(size=mag.shape)[mask]
        recon = np.fft.irfft(mag2 * np.exp(1j * ph2), n=n_fft).real
        out[start : start + n_fft] += recon * window
        norm[start : start + n_fft] += window**2
    norm = np.maximum(norm, 1e-8)
    y = out / norm
    y = np.where(norm < 1e-3, main, y)
    rms_m = float(np.sqrt(np.mean(main**2)) + 1e-12)
    rms_y = float(np.sqrt(np.mean(y**2)) + 1e-12)
    y *= rms_m / rms_y
    return y


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
            "ads_robot_target": "uncertain",
            "nota": (
                "Redirect experimental. CapCut moderno costuma AINDA legendar a black. "
                "Se a legenda precisa ser white, use mode=white_only."
            ),
        }
        peak = float(np.max(np.abs(y)) + 1e-12)
        if peak > 0.99:
            y *= 0.99 / peak
        return y.astype(np.float32), meta

    if mode in ("anti_analise", "anti-analise", "anti_analysis", "ads"):
        # Black dona do áudio + white sob mascaramento + micro-scramble leve
        p_aa = CloakParams(
            mode="anti_analise",
            decoy_db=p.decoy_db if p.decoy_db > -38 else -30.0,
            decoy_pre_emphasis=p.decoy_pre_emphasis,
            f_lo=p.f_lo,
            f_hi=p.f_hi,
            n_fft=p.n_fft,
            hop=p.hop,
            env_smooth_s=p.env_smooth_s,
            floor=max(p.floor, 0.06),
            max_peak_ratio=max(p.max_peak_ratio, 0.07),
            seed=p.seed,
            micro_scramble=p.micro_scramble if p.micro_scramble > 0 else 0.12,
            mask_under_speech=p.mask_under_speech if p.mask_under_speech > 0 else 0.85,
        )
        y = _inject_masked_white(main, dec, sr, p_aa)
        y = _micro_scramble_stt_band(y, sr, p_aa, rng)
        # reforço residual bem baixo (watermark extra, quase inaudível)
        y = _inject_quiet_white(
            y,
            dec,
            sr,
            CloakParams(
                decoy_db=min(-38.0, p_aa.decoy_db - 8.0),
                max_peak_ratio=0.025,
                env_smooth_s=p_aa.env_smooth_s,
                floor=0.03,
                seed=p.seed + 3,
            ),
        )
        corr = float(np.corrcoef(main, y)[0, 1]) if len(main) > 8 else 1.0
        meta = {
            "cloaker": True,
            "engine": "anti_analise_masked_white_plus_micro_scramble",
            "mode": "anti_analise",
            "decoy_db": p_aa.decoy_db,
            "micro_scramble": p_aa.micro_scramble,
            "mask_under_speech": p_aa.mask_under_speech,
            "corr_vs_black": corr,
            "human_hears": "black",
            "capcut_likely_hears": "mostly_black",
            "ads_robot_target": "confuse_audio_extract",
            "nota": (
                "Anti-análise: black principal + white dinâmica sob a fala + "
                "micro-scramble na banda de voz. Mira robô de ads (proxy STT), "
                "não garante aprovação. Humano deve ouvir a black."
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
        "ads_robot_target": "weak_watermark_only",
        "nota": (
            "Áudio black preservado (qualidade de anúncio). "
            "CapCut/TikTok VÃO legendar a black se ela for fala clara — "
            "isso é normal. Para tentar sujar análise de ads, use anti_analise."
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
