"""
Camada 3 — Dispersor de Fase (All-Pass Filter IIR de 4ª ordem).

Altera apenas a fase (atraso de grupo variável 2–15 ms),
mantendo a magnitude do espectro praticamente intacta —
espectralmente “invisível”, mas bagunça alinhamentos
temporais finos usados por alguns ASRs e watermark detectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from scipy.signal import lfilter, freqz


@dataclass
class ParametrosDispersor:
    """Parâmetros ajustáveis da Camada 3."""

    # Atraso de grupo alvo (ms) — controla quão “espalhada” fica a fase
    group_delay_min_ms: float = 2.0
    group_delay_max_ms: float = 12.0
    # Frequências de quebra normalizadas (0–1, fração de Nyquist) para seções de 1ª ordem
    # 4 seções cascateadas = 4ª ordem
    break_freqs_frac: Optional[List[float]] = None
    intensidade: float = 0.85  # 0 = off, 1 = full
    seed: Optional[int] = 7


class DispersorFase:
    """
    Filtro all-pass IIR de 4ª ordem (cascata de 4 seções de 1ª ordem).

    All-pass: |H(ω)| ≈ 1 para todas as frequências; só a fase muda.
    Analogia: como um espelho que não escurece a imagem, mas distorce
    o tempo em que cada cor chega — o “desenho” (espectro) parece igual,
    o “timing” interno muda.
    """

    def __init__(self, params: Optional[ParametrosDispersor] = None) -> None:
        self.params = params or ParametrosDispersor()

    def aplicar(
        self,
        audio: np.ndarray,
        sr: int,
        params: Optional[ParametrosDispersor] = None,
    ) -> Tuple[np.ndarray, dict]:
        """
        Aplica dispersor de fase all-pass.

        Args:
            audio: Sinal mono.
            sr: Taxa de amostragem.
            params: Sobrescreve parâmetros.

        Returns:
            Áudio com fase dispersa e metadados.
        """
        p = params or self.params
        try:
            y = self._garantir_mono(audio).astype(np.float64)
            if len(y) < 16:
                return y.astype(np.float32), {
                    "aplicada": False,
                    "aviso": "áudio muito curto",
                    "camada": 3,
                }

            rng = np.random.default_rng(p.seed)
            fracs = p.break_freqs_frac
            if not fracs or len(fracs) < 4:
                # 4 frequências de quebra espalhadas no espectro útil
                fracs = list(rng.uniform(0.05, 0.85, size=4))
                fracs = sorted(fracs)

            # Mapeia atraso de grupo desejado → coeficiente |r| do pólo
            # Para all-pass 1ª ordem: gd(0) ≈ (1-r)/(1+r) amostras (aprox.)
            gd_min = p.group_delay_min_ms * 1e-3 * sr
            gd_max = p.group_delay_max_ms * 1e-3 * sr
            # Distribui atraso entre as 4 seções
            delays = np.linspace(gd_min / 4.0, gd_max / 4.0, 4)

            b_total = np.array([1.0], dtype=np.float64)
            a_total = np.array([1.0], dtype=np.float64)
            coeficientes: list[dict] = []

            for frac, gd_sec in zip(fracs, delays):
                # r ∈ (0, 1): maior r → mais atraso de grupo perto da freq de quebra
                # Aprox: gd ≈ (1-r^2)/(1-2r cosθ + r^2) — usamos r a partir de gd médio
                r = self._r_from_group_delay(float(gd_sec))
                r = float(np.clip(r, 0.1, 0.95))
                # Ângulo do pólo (frequência de quebra)
                theta = float(frac) * np.pi  # 0..π
                # Seção real de 1ª ordem com pólo real negativo/positivo via cos
                # Usamos all-pass real clássico: H(z) = (a + z^-1)/(1 + a z^-1)
                # com a = -r * sign, mapeado de theta
                a_coef = -r * np.cos(theta)
                a_coef = float(np.clip(a_coef, -0.95, 0.95))

                # b = [a, 1], a = [1, a]  → all-pass 1ª ordem
                b_sec = np.array([a_coef, 1.0], dtype=np.float64)
                a_sec = np.array([1.0, a_coef], dtype=np.float64)

                b_total = np.convolve(b_total, b_sec)
                a_total = np.convolve(a_total, a_sec)
                coeficientes.append(
                    {
                        "a": a_coef,
                        "r": r,
                        "theta": theta,
                        "break_frac": float(frac),
                        "gd_amostras_alvo": float(gd_sec),
                    }
                )

            filtrado = lfilter(b_total, a_total, y)

            # Mistura com original conforme intensidade (0–1)
            intensidade = float(np.clip(p.intensidade, 0.0, 1.0))
            out = (1.0 - intensidade) * y + intensidade * filtrado

            # Renormaliza energia para magnitude espectral semelhante
            rms_in = float(np.sqrt(np.mean(y**2)) + 1e-12)
            rms_out = float(np.sqrt(np.mean(out**2)) + 1e-12)
            out = out * (rms_in / rms_out)
            out = np.clip(out, -1.0, 1.0)

            # Métricas de “invisibilidade” espectral
            mag_diff = self._diff_magnitude_db(y, out, sr)

            meta = {
                "aplicada": True,
                "camada": 3,
                "nome": "dispersor_fase_allpass",
                "ordem": 4,
                "coeficientes": coeficientes,
                "group_delay_min_ms": p.group_delay_min_ms,
                "group_delay_max_ms": p.group_delay_max_ms,
                "intensidade": intensidade,
                "diff_magnitude_media_db": mag_diff,
                "b": b_total.tolist(),
                "a": a_total.tolist(),
            }
            return out.astype(np.float32), meta

        except Exception as exc:
            return np.asarray(audio, dtype=np.float32), {
                "aplicada": False,
                "erro": str(exc),
                "camada": 3,
            }

    @staticmethod
    def _r_from_group_delay(gd_samples: float) -> float:
        """
        Estima |r| a partir do atraso de grupo desejado (amostras).
        Para all-pass 1ª ordem em DC: gd ≈ (1-r)/(1+r).
        """
        gd = max(float(gd_samples), 0.01)
        # (1-r)/(1+r) = gd  →  1-r = gd + gd*r → 1-gd = r(1+gd) → r = (1-gd)/(1+gd)
        # Mas gd pode ser >> 1; usamos mapeamento suave
        # r = 1 - 1/(1+gd)  → gd grande ⇒ r perto de 1
        r = 1.0 - 1.0 / (1.0 + gd / 4.0)
        return float(np.clip(r, 0.1, 0.95))

    @staticmethod
    def _diff_magnitude_db(a: np.ndarray, b: np.ndarray, sr: int) -> float:
        """Diferença média de magnitude em dB (deve ser ~0 para all-pass)."""
        try:
            # Ignora transitório inicial do IIR (~50 ms)
            skip = min(len(a), len(b), max(0, int(0.05 * sr)))
            a2, b2 = a[skip:], b[skip:]
            n = min(len(a2), len(b2), 8192)
            n = int(2 ** np.floor(np.log2(max(n, 256))))
            if n < 256:
                return 0.0
            wa = np.hanning(n)
            fa = np.fft.rfft(a2[:n] * wa)
            fb = np.fft.rfft(b2[:n] * wa)
            ma = np.abs(fa) + 1e-12
            mb = np.abs(fb) + 1e-12
            # Mediana é mais robusta a bins quase nulos
            return float(np.median(np.abs(20.0 * np.log10(mb / ma))))
        except Exception:
            return -1.0

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

    def resposta_frequencia(
        self, sr: int, params: Optional[ParametrosDispersor] = None, n_fft: int = 2048
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calcula magnitude e fase da resposta em frequência do all-pass atual.
        Útil para o dashboard (provar que |H|≈1).
        """
        p = params or self.params
        # Aplica em impulso e usa FFT — ou reconstrói coeficientes
        impulso = np.zeros(n_fft)
        impulso[0] = 1.0
        y, meta = self.aplicar(impulso, sr, p)
        if not meta.get("aplicada"):
            w = np.linspace(0, np.pi, n_fft // 2 + 1)
            return w, np.ones_like(w), np.zeros_like(w)
        b = np.array(meta["b"], dtype=np.float64)
        a = np.array(meta["a"], dtype=np.float64)
        w, h = freqz(b, a, worN=n_fft)
        return w, np.abs(h), np.angle(h)
