"""
Camada 1 — Mascaramento Psicoacústico.

Injeta tons puros próximos aos formantes da voz (2.5–3.5 kHz),
modulados pelo envelope do sinal, de forma que o ouvido humano
quase não perceba a diferença (mascaramento: som forte esconde
som fraco na mesma região de frequência).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.signal import hilbert, get_window


@dataclass
class ParametrosMascaramento:
    """Parâmetros ajustáveis da Camada 1."""

    freq_min_hz: float = 2500.0
    freq_max_hz: float = 3500.0
    n_tons: int = 3
    intensidade_db: float = -28.0  # relativo ao envelope local
    n_fft: int = 2048
    hop_length: int = 512
    usar_fase_aleatoria: bool = True
    seed: Optional[int] = 42


class MascaramentoPsicoacustico:
    """
    Aplica mascaramento psicoacústico via FFT + manipulação de fase.

    Analogia: como sussurrar no meio de uma festa barulhenta —
    a voz alta da festa (formantes) esconde o sussurro (tons injetados).
    """

    def __init__(self, params: Optional[ParametrosMascaramento] = None) -> None:
        self.params = params or ParametrosMascaramento()

    def aplicar(
        self,
        audio: np.ndarray,
        sr: int,
        params: Optional[ParametrosMascaramento] = None,
    ) -> Tuple[np.ndarray, dict]:
        """
        Aplica mascaramento psicoacústico ao áudio.

        Args:
            audio: Sinal mono float32/float64, faixa tipicamente [-1, 1].
            sr: Taxa de amostragem em Hz.
            params: Sobrescreve parâmetros da instância.

        Returns:
            Áudio protegido e dicionário de metadados da camada.
        """
        p = params or self.params
        try:
            y = self._garantir_mono(audio).astype(np.float64)
            if len(y) == 0:
                return y.astype(np.float32), {"erro": "áudio vazio", "aplicada": False}

            # Nyquist: se a taxa for baixa demais, não dá para injetar nessas freqs
            nyquist = sr / 2.0
            freq_min = min(p.freq_min_hz, nyquist * 0.9)
            freq_max = min(p.freq_max_hz, nyquist * 0.95)
            if freq_min >= freq_max:
                return y.astype(np.float32), {
                    "aplicada": False,
                    "aviso": "taxa de amostragem insuficiente para formantes alvo",
                }

            rng = np.random.default_rng(p.seed)
            envelope = self._envelope_hilbert(y)
            # Suaviza envelope para evitar cliques
            envelope = self._suavizar(envelope, max(1, sr // 200))

            t = np.arange(len(y), dtype=np.float64) / float(sr)
            freqs = np.linspace(freq_min, freq_max, max(1, p.n_tons))
            ganho_linear = 10.0 ** (p.intensidade_db / 20.0)

            mascara = np.zeros_like(y)
            fases: list[float] = []

            for f in freqs:
                if p.usar_fase_aleatoria:
                    fase = float(rng.uniform(0, 2 * np.pi))
                else:
                    fase = 0.0
                fases.append(fase)
                # Tom puro modulado pelo envelope da voz
                tom = np.sin(2.0 * np.pi * f * t + fase)
                mascara += tom * envelope * ganho_linear

            # Normaliza a energia da máscara para não saturar
            pico_orig = max(float(np.max(np.abs(y))), 1e-12)
            # n_tons tons somados: divide para manter nível alvo
            mascara = mascara / max(1, p.n_tons)
            limite = pico_orig * ganho_linear * 1.2
            pico_mask = float(np.max(np.abs(mascara))) + 1e-12
            if pico_mask > limite:
                mascara *= limite / pico_mask

            rms_antes = float(np.sqrt(np.mean(mascara**2)) + 1e-12)

            # Refinamento em domínio de frequência: alinha fase local (FFT)
            mascara = self._refinar_fase_fft(y, mascara, p.n_fft, p.hop_length, rng)

            # Restaura energia (FFT/OLA não pode explodir o ganho)
            rms_depois = float(np.sqrt(np.mean(mascara**2)) + 1e-12)
            mascara *= rms_antes / rms_depois
            pico_mask = float(np.max(np.abs(mascara))) + 1e-12
            if pico_mask > limite:
                mascara *= limite / pico_mask

            protegido = y + mascara
            # Preserva escala se não houver clipping severo
            peak = float(np.max(np.abs(protegido)))
            if peak > 1.0:
                protegido = protegido / peak * 0.99
            else:
                protegido = self._limitar_soft(protegido)

            meta = {
                "aplicada": True,
                "camada": 1,
                "nome": "mascaramento_psicoacustico",
                "frequencias_hz": [float(f) for f in freqs],
                "fases_rad": fases,
                "intensidade_db": p.intensidade_db,
                "n_fft": p.n_fft,
                "rms_mascara": float(np.sqrt(np.mean(mascara**2))),
                "snr_estimado_db": self._snr_db(y, mascara),
            }
            return protegido.astype(np.float32), meta

        except Exception as exc:  # fallback seguro: devolve original
            return audio.astype(np.float32), {
                "aplicada": False,
                "erro": str(exc),
                "camada": 1,
            }

    def _refinar_fase_fft(
        self,
        original: np.ndarray,
        mascara: np.ndarray,
        n_fft: int,
        hop: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """
        Ajusta a fase da máscara frame a frame para coincidir parcialmente
        com a fase do original (mais inaudível) + pequeno jitter.
        """
        try:
            n = len(original)
            if n < n_fft:
                return mascara

            window = get_window("hann", n_fft, fftbins=True).astype(np.float64)
            out = np.zeros(n, dtype=np.float64)
            norm = np.zeros(n, dtype=np.float64)

            # Análise com janela; síntese COLA com hop = n_fft//4 típico
            for start in range(0, n - n_fft + 1, hop):
                end = start + n_fft
                frame_o = original[start:end] * window
                frame_m = mascara[start:end] * window

                spec_o = np.fft.rfft(frame_o)
                spec_m = np.fft.rfft(frame_m)

                mag_m = np.abs(spec_m)
                fase_o = np.angle(spec_o)
                # Mistura fase do original com jitter leve (manipulação de fase)
                jitter = rng.uniform(-0.15, 0.15, size=fase_o.shape)
                fase_nova = fase_o + jitter
                spec_novo = mag_m * np.exp(1j * fase_nova)

                recon = np.fft.irfft(spec_novo, n=n_fft).real
                out[start:end] += recon * window
                norm[start:end] += window**2

            # Cauda residual sem janela completa
            if n >= n_fft:
                tail = n - ((n - n_fft) // hop * hop + n_fft)
                if tail > 0:
                    out[-hop:] += mascara[-hop:]
                    norm[-hop:] += 1.0

            norm = np.maximum(norm, 1e-8)
            refined = out / norm
            # Onde a norma é fraca (bordas), mantém máscara original
            fraco = norm < 1e-3
            refined[fraco] = mascara[fraco]
            return refined
        except Exception:
            return mascara

    @staticmethod
    def _envelope_hilbert(y: np.ndarray) -> np.ndarray:
        """Envelope analítico (Hilbert) — contorno de volume da voz."""
        try:
            analytic = hilbert(y)
            env = np.abs(analytic)
            # Evita envelope zero em silêncio total
            return env + 1e-6
        except Exception:
            return np.abs(y) + 1e-6

    @staticmethod
    def _suavizar(x: np.ndarray, win: int) -> np.ndarray:
        if win <= 1:
            return x
        kernel = np.ones(win, dtype=np.float64) / win
        return np.convolve(x, kernel, mode="same")

    @staticmethod
    def _garantir_mono(audio: np.ndarray) -> np.ndarray:
        a = np.asarray(audio)
        if a.ndim == 1:
            return a
        if a.ndim == 2:
            # (channels, samples) ou (samples, channels)
            if a.shape[0] <= 8 and a.shape[0] < a.shape[1]:
                return np.mean(a, axis=0)
            return np.mean(a, axis=1)
        return a.flatten()

    @staticmethod
    def _limitar_soft(y: np.ndarray, lim: float = 0.99) -> np.ndarray:
        """Soft clip suave para evitar clipping duro."""
        return lim * np.tanh(y / lim)

    @staticmethod
    def _snr_db(sinal: np.ndarray, ruido: np.ndarray) -> float:
        ps = float(np.mean(sinal**2)) + 1e-12
        pr = float(np.mean(ruido**2)) + 1e-12
        return float(10.0 * np.log10(ps / pr))
