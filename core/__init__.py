"""
AudioShield - Core de proteção invisível de áudio.

Exporta as 4 camadas e o pipeline orquestrador.
"""

from core.camada1_mascaramento import MascaramentoPsicoacustico
from core.camada2_ultrassom import InjecaoUltrassonica
from core.camada3_dispersor import DispersorFase
from core.camada4_adversarial import WatermarkingAdversarial
from core.pipeline import AudioShieldPipeline, PipelineConfig

__all__ = [
    "MascaramentoPsicoacustico",
    "InjecaoUltrassonica",
    "DispersorFase",
    "WatermarkingAdversarial",
    "AudioShieldPipeline",
    "PipelineConfig",
]

__version__ = "1.0.0"
