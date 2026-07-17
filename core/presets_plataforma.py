"""
Presets por plataforma / editor (CapCut, TikTok, etc.).

CapCut e apps sociais:
  - jogam fora ultrassom
  - usam ASR forte na faixa da voz
  → priorizar anti-legenda agressiva na fala
"""

from __future__ import annotations

from typing import Any, Dict

from core.camada1_mascaramento import ParametrosMascaramento
from core.camada2_ultrassom import ParametrosUltrassom
from core.camada3_dispersor import ParametrosDispersor
from core.camada4_adversarial import ParametrosAdversarial
from core.pipeline import PipelineConfig

# Plataformas com compressão pesada + legenda automática
SOCIAL_HEAVY = {
    "tiktok",
    "kwai",
    "instagram",
    "facebook",
    "whatsapp",
    "capcut",
    "youtube_shorts",
}


def config_para_plataforma(platform_id: str) -> PipelineConfig:
    """Monta PipelineConfig otimizado para a plataforma escolhida."""
    pid = (platform_id or "generic").lower()

    if pid in SOCIAL_HEAVY or pid == "capcut":
        # Anti-CapCut / anti-legenda de rede social
        return PipelineConfig(
            aplicar_camada1=True,
            aplicar_camada2=False,  # ultrassom morre no encode
            aplicar_camada3=True,
            aplicar_camada4=True,
            mascaramento=ParametrosMascaramento(
                intensidade_db=-18.0,
                n_tons=5,
                freq_min_hz=2200.0,
                freq_max_hz=3800.0,
            ),
            ultrassom=ParametrosUltrassom(volume_db=-50.0),
            dispersor=ParametrosDispersor(
                group_delay_min_ms=4.0,
                group_delay_max_ms=18.0,
                intensidade=1.0,
            ),
            adversarial=ParametrosAdversarial(
                forca="aggressive",
                usar_whisper=False,
                epsilon_db=-16.0,
            ),
        )

    if pid in ("youtube", "linkedin"):
        return PipelineConfig(
            adversarial=ParametrosAdversarial(forca="balanced", usar_whisper=False),
            mascaramento=ParametrosMascaramento(intensidade_db=-24.0, n_tons=4),
            dispersor=ParametrosDispersor(intensidade=0.9),
        )

    # genérico / trello / x
    return PipelineConfig(
        adversarial=ParametrosAdversarial(forca="aggressive", usar_whisper=False),
        mascaramento=ParametrosMascaramento(intensidade_db=-20.0, n_tons=4),
        ultrassom=ParametrosUltrassom(volume_db=-45.0),
        dispersor=ParametrosDispersor(intensidade=0.95),
    )


def resumo_preset(platform_id: str) -> Dict[str, Any]:
    cfg = config_para_plataforma(platform_id)
    return {
        "platform": platform_id,
        "camada2_ultrassom": cfg.aplicar_camada2,
        "anti_legenda_forca": cfg.adversarial.forca,
        "mascaramento_db": cfg.mascaramento.intensidade_db,
    }
