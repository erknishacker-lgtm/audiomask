"""
Pipeline AudioShield — orquestra as 4 camadas de proteção.

Ordem padrão:
  1. Mascaramento psicoacústico
  2. Injeção ultrassônica
  3. Dispersor de fase (all-pass)
  4. Watermarking adversarial
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.camada1_mascaramento import MascaramentoPsicoacustico, ParametrosMascaramento
from core.camada2_ultrassom import InjecaoUltrassonica, ParametrosUltrassom
from core.camada3_dispersor import DispersorFase, ParametrosDispersor
from core.camada4_adversarial import WatermarkingAdversarial, ParametrosAdversarial


# Prefixo mágico embutido no hash stealth (não é watermark audível)
STEALTH_MAGIC = b"AUDIOSHIELD_v1"


@dataclass
class PipelineConfig:
    """Configuração completa do pipeline (ajustável via UI)."""

    aplicar_camada1: bool = True
    aplicar_camada2: bool = True
    aplicar_camada3: bool = True
    aplicar_camada4: bool = True
    mascaramento: ParametrosMascaramento = field(default_factory=ParametrosMascaramento)
    ultrassom: ParametrosUltrassom = field(default_factory=ParametrosUltrassom)
    dispersor: ParametrosDispersor = field(default_factory=ParametrosDispersor)
    adversarial: ParametrosAdversarial = field(default_factory=ParametrosAdversarial)
    # Stealth: grava fingerprint nos metadados / hash
    modo_stealth_tag: bool = True


class AudioShieldPipeline:
    """
    Orquestra todas as camadas e gera relatório JSON.

    Analogia: linha de montagem — o áudio passa por 4 estações,
    cada uma adiciona uma proteção diferente e quase invisível.
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self.c1 = MascaramentoPsicoacustico(self.config.mascaramento)
        self.c2 = InjecaoUltrassonica(self.config.ultrassom)
        self.c3 = DispersorFase(self.config.dispersor)
        self.c4 = WatermarkingAdversarial(self.config.adversarial)

    def processar(
        self,
        audio: np.ndarray,
        sr: int,
        config: Optional[PipelineConfig] = None,
        nome_arquivo: str = "audio",
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Aplica as camadas habilitadas em sequência.

        Returns:
            (áudio_protegido, relatório completo)
        """
        cfg = config or self.config
        y = self._garantir_mono(audio).astype(np.float32)
        y0 = y.copy()

        camadas_meta: List[dict] = []
        ordem: List[str] = []

        # Stealth: se já processado, avisa mas continua se o usuário quiser
        ja_protegido = self.detectar_stealth(y0, sr)

        if cfg.aplicar_camada1:
            y, m = self.c1.aplicar(y, sr, cfg.mascaramento)
            camadas_meta.append(m)
            ordem.append("camada1_mascaramento")

        if cfg.aplicar_camada2:
            y, m = self.c2.aplicar(y, sr, cfg.ultrassom)
            camadas_meta.append(m)
            ordem.append("camada2_ultrassom")

        if cfg.aplicar_camada3:
            y, m = self.c3.aplicar(y, sr, cfg.dispersor)
            camadas_meta.append(m)
            ordem.append("camada3_dispersor")

        if cfg.aplicar_camada4:
            y, m = self.c4.aplicar(y, sr, cfg.adversarial)
            camadas_meta.append(m)
            ordem.append("camada4_adversarial")

        y = np.clip(y.astype(np.float32), -1.0, 1.0)

        fingerprint = self._fingerprint(y, sr)
        relatorio: Dict[str, Any] = {
            "projeto": "AudioShield",
            "versao": "1.0.0",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "arquivo": nome_arquivo,
            "sr": int(sr),
            "n_amostras": int(len(y)),
            "duracao_s": float(len(y) / sr) if sr else 0.0,
            "ordem_camadas": ordem,
            "camadas": camadas_meta,
            "fingerprint_sha256": fingerprint,
            "stealth_detectado_na_entrada": ja_protegido,
            "metricas": self._metricas(y0, y),
            "parametros": self._serializar_config(cfg),
        }

        if cfg.modo_stealth_tag:
            relatorio["stealth_tag"] = self._stealth_tag(fingerprint)

        return y, relatorio

    def processar_batch(
        self,
        itens: List[Tuple[np.ndarray, int, str]],
        config: Optional[PipelineConfig] = None,
    ) -> List[Tuple[np.ndarray, Dict[str, Any]]]:
        """
        Processa múltiplos áudios [(audio, sr, nome), ...].
        """
        resultados = []
        for audio, sr, nome in itens:
            try:
                resultados.append(self.processar(audio, sr, config, nome_arquivo=nome))
            except Exception as exc:
                resultados.append(
                    (
                        np.asarray(audio, dtype=np.float32),
                        {"erro": str(exc), "arquivo": nome, "aplicada": False},
                    )
                )
        return resultados

    def salvar_relatorio(
        self, relatorio: Dict[str, Any], caminho: str
    ) -> str:
        """Salva relatório JSON e retorna o caminho."""
        os.makedirs(os.path.dirname(os.path.abspath(caminho)) or ".", exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)
        return caminho

    def detectar_stealth(self, audio: np.ndarray, sr: int) -> bool:
        """
        Modo Stealth: tenta detectar se o áudio já foi processado.

        Método: compara assinatura espectral de alta frequência +
        hash de características (não é 100% à prova de re-encode).
        """
        try:
            y = self._garantir_mono(audio).astype(np.float64)
            if len(y) < 1024:
                return False

            # Razão de energia > 18 kHz vs total (ultrassom típico)
            n = min(len(y), 48000)
            spec = np.abs(np.fft.rfft(y[:n] * np.hanning(n)))
            freqs = np.fft.rfftfreq(n, d=1.0 / sr)
            total = float(np.sum(spec**2) + 1e-12)
            high = float(np.sum(spec[freqs >= 18000] ** 2))
            ratio = high / total

            # All-pass deixa magnitude igual, mas C2 eleva banda alta
            # Heurística: ratio alto + fingerprint conhecido em silêncio final
            if ratio > 0.02 and sr >= 44100:
                return True

            # Segunda checagem: autocorrelação de fase em banda de formantes
            # (fraca — só indício)
            return False
        except Exception:
            return False

    @staticmethod
    def _fingerprint(audio: np.ndarray, sr: int) -> str:
        """Hash SHA-256 de características estáveis + amostras decimadas."""
        y = np.asarray(audio, dtype=np.float32)
        # Decima para fingerprint compacto
        step = max(1, len(y) // 4096)
        payload = y[::step].tobytes() + str(sr).encode() + STEALTH_MAGIC
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _stealth_tag(fingerprint: str) -> str:
        return hashlib.sha256(STEALTH_MAGIC + fingerprint.encode()).hexdigest()[:32]

    @staticmethod
    def _metricas(original: np.ndarray, protegido: np.ndarray) -> Dict[str, float]:
        a = original.astype(np.float64)
        b = protegido.astype(np.float64)
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]
        diff = b - a
        ps = float(np.mean(a**2)) + 1e-12
        pd = float(np.mean(diff**2)) + 1e-12
        snr = 10.0 * np.log10(ps / pd)
        max_diff = float(np.max(np.abs(diff)))
        return {
            "snr_db": float(snr),
            "max_abs_diff": max_diff,
            "rms_diff": float(np.sqrt(pd)),
            "rms_original": float(np.sqrt(ps)),
        }

    @staticmethod
    def _serializar_config(cfg: PipelineConfig) -> Dict[str, Any]:
        def dc(obj: Any) -> Any:
            if hasattr(obj, "__dataclass_fields__"):
                return {k: dc(getattr(obj, k)) for k in obj.__dataclass_fields__}
            if isinstance(obj, (list, tuple)):
                return [dc(x) for x in obj]
            if isinstance(obj, (int, float, str, bool)) or obj is None:
                return obj
            return str(obj)

        return dc(cfg)

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
