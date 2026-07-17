"""
Camada 2 — Injeção Ultrassônica.

Injeta ruído branco modulado em ~19.5 kHz (ultrassom),
quase inaudível para adultos, mas captado por microfones
e por muitos modelos de ASR (que “escutam” o espectro inteiro).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.signal import butter, filtfilt, sosfiltfilt


@dataclass
class ParametrosUltrassom:
    """Parâmetros ajustáveis da Camada 2."""

    freq_portadora_hz: float = 19500.0
    volume_db: float = -45.0  # entre -40 e -50 típico
    cutoff_passa_alta_hz: float = 18000.0
    ordem_filtro: int = 4
    seed: Optional[int] = 123
    largura_banda_hz: float = 1000.0  # ruído em torno da portadora


class InjecaoUltrassonica:
    """
    Injeta componente ultrassônica imperceptível.

    Analogia: como um apito de cachorro — humanos quase não ouvem,
    mas o microfone (e o software) registram.
    """

    def __init__(self, params: Optional[ParametrosUltrassom] = None) -> None:
        self.params = params or ParametrosUltrassom()

    def aplicar(
        self,
        audio: np.ndarray,
        sr: int,
        params: Optional[ParametrosUltrassom] = None,
    ) -> Tuple[np.ndarray, dict]:
        """
        Aplica injeção ultrassônica.

        Args:
            audio: Sinal mono.
            sr: Taxa de amostragem (ideal ≥ 44.1 kHz).
            params: Sobrescreve parâmetros.

        Returns:
            Áudio com ultrassom misturado e metadados.
        """
        p = params or self.params
        try:
            y = self._garantir_mono(audio).astype(np.float64)
            nyquist = sr / 2.0

            if p.freq_portadora_hz >= nyquist:
                return y.astype(np.float32), {
                    "aplicada": False,
                    "aviso": (
                        f"Taxa {sr} Hz não suporta {p.freq_portadora_hz} Hz. "
                        "Use ≥ 44.1 kHz (recomendado 48 kHz)."
                    ),
                    "camada": 2,
                }

            rng = np.random.default_rng(p.seed)
            n = len(y)
            t = np.arange(n, dtype=np.float64) / float(sr)

            # Ruído branco
            ruido = rng.standard_normal(n)

            # Filtra o ruído para banda alta (passa-alta) e opcionalmente banda estreita
            cutoff = min(p.cutoff_passa_alta_hz, nyquist * 0.95)
            if cutoff >= nyquist * 0.99:
                cutoff = nyquist * 0.85

            ruido_hp = self._passa_alta(ruido, sr, cutoff, p.ordem_filtro)

            # Modulação AM com portadora ultrassônica
            portadora = np.cos(2.0 * np.pi * p.freq_portadora_hz * t)
            # Envelope lento do ruído para não soar como tom puro
            env_lento = self._envelope_lento(ruido_hp, sr)
            ultrasom = ruido_hp * portadora * (0.5 + 0.5 * env_lento)

            # Garante que só a região alta fique no mix (passa-alta final)
            ultrasom = self._passa_alta(ultrasom, sr, cutoff, p.ordem_filtro)

            # Volume alvo em dB relativo ao RMS do sinal original
            rms_y = float(np.sqrt(np.mean(y**2)) + 1e-12)
            rms_u = float(np.sqrt(np.mean(ultrasom**2)) + 1e-12)
            ganho = (rms_y * (10.0 ** (p.volume_db / 20.0))) / rms_u
            ultrasom *= ganho

            # Clamp de segurança: nunca acima de -35 dB do pico
            pico_y = max(float(np.max(np.abs(y))), 1e-12)
            pico_u = float(np.max(np.abs(ultrasom)))
            max_permitido = pico_y * (10.0 ** (-35.0 / 20.0))
            if pico_u > max_permitido:
                ultrasom *= max_permitido / (pico_u + 1e-12)

            protegido = y + ultrasom
            protegido = np.clip(protegido, -1.0, 1.0)

            meta = {
                "aplicada": True,
                "camada": 2,
                "nome": "injecao_ultrassonica",
                "freq_portadora_hz": p.freq_portadora_hz,
                "volume_db": p.volume_db,
                "cutoff_hp_hz": cutoff,
                "sr": sr,
                "rms_ultrassom": float(np.sqrt(np.mean(ultrasom**2))),
                "snr_db": self._snr_db(y, ultrasom),
            }
            return protegido.astype(np.float32), meta

        except Exception as exc:
            return np.asarray(audio, dtype=np.float32), {
                "aplicada": False,
                "erro": str(exc),
                "camada": 2,
            }

    def _passa_alta(
        self, x: np.ndarray, sr: int, cutoff: float, ordem: int
    ) -> np.ndarray:
        """Filtro passa-alta Butterworth (SOS, estável)."""
        try:
            nyq = sr / 2.0
            wn = min(cutoff / nyq, 0.99)
            if wn <= 0.01:
                return x
            sos = butter(ordem, wn, btype="high", output="sos")
            return sosfiltfilt(sos, x)
        except Exception:
            # Fallback simples com butter b/a
            try:
                b, a = butter(ordem, min(cutoff / (sr / 2.0), 0.99), btype="high")
                return filtfilt(b, a, x)
            except Exception:
                return x

    @staticmethod
    def _envelope_lento(x: np.ndarray, sr: int) -> np.ndarray:
        win = max(1, sr // 50)  # ~20 ms
        mag = np.abs(x)
        kernel = np.ones(win) / win
        env = np.convolve(mag, kernel, mode="same")
        m = float(np.max(env)) + 1e-12
        return env / m

    @staticmethod
    def _garantir_mono(audio: np.ndarray) -> np.ndarray:
        a = np.asarray(audio)
        if a.ndim == 1:
            return a
        if a.ndim == 2:
            if a.shape[0] <= 8 and a.shape[0] < a.shape[1]:
                return np.mean(a, axis=0)
            return np.mean(a, axis=1)
        return a.flatten()

    @staticmethod
    def _snr_db(sinal: np.ndarray, ruido: np.ndarray) -> float:
        ps = float(np.mean(sinal**2)) + 1e-12
        pr = float(np.mean(ruido**2)) + 1e-12
        return float(10.0 * np.log10(ps / pr))
