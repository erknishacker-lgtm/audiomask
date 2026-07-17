"""Utilitários AudioShield: I/O, espectro, validação e vídeo."""

from utils.audio_io import carregar_audio, salvar_audio, gerar_voz_sintetica
from utils.espectro import gerar_espectrograma, figura_antes_depois
from utils.validacao import validar_inaudibilidade, resumo_validacao
from utils.video_io import (
    eh_video,
    extrair_audio_do_video,
    ffmpeg_disponivel,
    proteger_video,
    remux_audio_no_video,
)

__all__ = [
    "carregar_audio",
    "salvar_audio",
    "gerar_voz_sintetica",
    "gerar_espectrograma",
    "figura_antes_depois",
    "validar_inaudibilidade",
    "resumo_validacao",
    "eh_video",
    "extrair_audio_do_video",
    "ffmpeg_disponivel",
    "proteger_video",
    "remux_audio_no_video",
]
