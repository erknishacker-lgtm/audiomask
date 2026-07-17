"""
I/O de vídeo MP4/MOV/WEBM para o AudioShield.

Fluxo (como trocar só a trilha sonora do filme):
  1. Extrai o áudio do vídeo (ffmpeg)
  2. Processa com as 4 camadas
  3. Remonta o vídeo com o áudio protegido (cópia do vídeo, reencode do áudio)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from utils.audio_io import carregar_audio, salvar_audio


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def ffmpeg_disponivel() -> bool:
    """Retorna True se o binário ffmpeg estiver no PATH."""
    return shutil.which("ffmpeg") is not None


def ffprobe_disponivel() -> bool:
    return shutil.which("ffprobe") is not None


def eh_video(nome_ou_caminho: str) -> bool:
    """Detecta extensão de vídeo suportada."""
    ext = os.path.splitext(str(nome_ou_caminho).lower())[1]
    return ext in VIDEO_EXTS


def extrair_audio_do_video(
    caminho_video: str,
    sr_alvo: Optional[int] = 48000,
    mono: bool = True,
) -> Tuple[np.ndarray, int, Dict[str, Any]]:
    """
    Extrai áudio de um arquivo de vídeo.

    Args:
        caminho_video: caminho do MP4/etc.
        sr_alvo: reamostragem (None = nativa).
        mono: força mono.

    Returns:
        (audio float32, sample_rate, metadados)
    """
    _exigir_ffmpeg()
    if not os.path.isfile(caminho_video):
        raise FileNotFoundError(f"Vídeo não encontrado: {caminho_video}")

    info = inspecionar_video(caminho_video)
    with tempfile.TemporaryDirectory(prefix="audioshield_vid_") as tmp:
        wav_path = os.path.join(tmp, "audio.wav")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            caminho_video,
            "-vn",
            "-acodec",
            "pcm_s16le",
        ]
        if mono:
            cmd += ["-ac", "1"]
        if sr_alvo:
            cmd += ["-ar", str(int(sr_alvo))]
        cmd.append(wav_path)

        _rodar(cmd, "extrair áudio do vídeo")
        y, sr = carregar_audio(wav_path)
        meta = {
            "origem": "video",
            "caminho_video": os.path.abspath(caminho_video),
            "sr_audio": int(sr),
            "duracao_audio_s": float(len(y) / sr) if sr else 0.0,
            "video_info": info,
        }
        return y.astype(np.float32), int(sr), meta


def extrair_audio_de_bytes(
    data: bytes,
    nome: str = "video.mp4",
    sr_alvo: Optional[int] = 48000,
) -> Tuple[np.ndarray, int, Dict[str, Any], str]:
    """
    Extrai áudio a partir de bytes (upload Streamlit).

    Returns:
        (audio, sr, meta, caminho_temporario_do_video)
        O caller deve apagar o caminho temporário quando não precisar mais
        (ou chamar limpar_temp).
    """
    _exigir_ffmpeg()
    ext = os.path.splitext(nome)[1].lower() or ".mp4"
    if ext not in VIDEO_EXTS:
        ext = ".mp4"

    fd, path = tempfile.mkstemp(suffix=ext, prefix="audioshield_up_")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(data)
        y, sr, meta = extrair_audio_do_video(path, sr_alvo=sr_alvo)
        meta["nome_original"] = nome
        meta["temp_video"] = path
        return y, sr, meta, path
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def remux_audio_no_video(
    caminho_video: str,
    audio: np.ndarray,
    sr: int,
    caminho_saida: str,
    codec_audio: str = "aac",
    bitrate_audio: str = "192k",
    copiar_video: bool = True,
) -> str:
    """
    Substitui a trilha de áudio do vídeo pelo áudio protegido.

    Por padrão copia o stream de vídeo sem reencodar (rápido, sem perda visual).
    O áudio é reencodado em AAC (compatível com MP4).

    Returns:
        Caminho do arquivo de saída.
    """
    _exigir_ffmpeg()
    if not os.path.isfile(caminho_video):
        raise FileNotFoundError(caminho_video)

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)) or ".", exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="audioshield_mux_") as tmp:
        wav_path = os.path.join(tmp, "protegido.wav")
        salvar_audio(wav_path, audio, sr, formato="wav")

        # -map 0:v  vídeo do original
        # -map 1:a  áudio do WAV protegido
        # -shortest  corta no menor (evita sobra se durações divergirem)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            caminho_video,
            "-i",
            wav_path,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
        ]
        if copiar_video:
            cmd += ["-c:v", "copy"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

        cmd += [
            "-c:a",
            codec_audio,
            "-b:a",
            bitrate_audio,
            "-shortest",
            "-movflags",
            "+faststart",
            caminho_saida,
        ]
        _rodar(cmd, "remux áudio protegido no vídeo")

    return caminho_saida


def proteger_video(
    caminho_video: str,
    pipeline,
    caminho_saida: str,
    config=None,
    sr_alvo: int = 48000,
    bitrate_audio: str = "192k",
) -> Tuple[str, Dict[str, Any]]:
    """
    Pipeline completo: extrai → protege → remux.

    Args:
        caminho_video: MP4 de entrada
        pipeline: instância AudioShieldPipeline
        caminho_saida: MP4 de saída
        config: PipelineConfig opcional
        sr_alvo: taxa para processamento (ultrassom precisa ≥ 44.1 kHz)
        bitrate_audio: bitrate AAC de saída

    Returns:
        (caminho_saida, relatório)
    """
    y, sr, meta_vid = extrair_audio_do_video(caminho_video, sr_alvo=sr_alvo)
    nome = os.path.basename(caminho_video)
    yp, rel = pipeline.processar(y, sr, config, nome_arquivo=nome)
    remux_audio_no_video(
        caminho_video,
        yp,
        sr,
        caminho_saida,
        bitrate_audio=bitrate_audio,
    )
    rel["video"] = meta_vid
    rel["saida_video"] = os.path.abspath(caminho_saida)
    rel["bitrate_audio"] = bitrate_audio
    return caminho_saida, rel


def video_para_bytes(caminho: str) -> bytes:
    """Lê arquivo de vídeo em bytes (download Streamlit)."""
    with open(caminho, "rb") as f:
        return f.read()


def inspecionar_video(caminho: str) -> Dict[str, Any]:
    """Metadados básicos via ffprobe (fallback mínimo sem probe)."""
    if not ffprobe_disponivel():
        return {"caminho": caminho, "ffprobe": False}
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            caminho,
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        data = json.loads(out.decode("utf-8", errors="replace"))
        streams = data.get("streams") or []
        video_s = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio_s = next((s for s in streams if s.get("codec_type") == "audio"), {})
        fmt = data.get("format") or {}
        return {
            "ffprobe": True,
            "duracao_s": float(fmt.get("duration") or 0),
            "tamanho_bytes": int(fmt.get("size") or 0),
            "formato": fmt.get("format_name"),
            "video_codec": video_s.get("codec_name"),
            "largura": video_s.get("width"),
            "altura": video_s.get("height"),
            "audio_codec": audio_s.get("codec_name"),
            "audio_sr": audio_s.get("sample_rate"),
            "audio_canais": audio_s.get("channels"),
            "tem_audio": bool(audio_s),
        }
    except Exception as exc:
        return {"ffprobe": False, "erro": str(exc)}


def limpar_temp(caminho: Optional[str]) -> None:
    """Remove arquivo temporário se existir."""
    if not caminho:
        return
    try:
        if os.path.isfile(caminho):
            os.unlink(caminho)
    except OSError:
        pass


def _exigir_ffmpeg() -> None:
    if not ffmpeg_disponivel():
        raise RuntimeError(
            "ffmpeg não encontrado no PATH. "
            "Instale com: brew install ffmpeg  (macOS) "
            "ou: sudo apt-get install ffmpeg  (Linux). "
            "É obrigatório para processar MP4."
        )


def _rodar(cmd: list, contexto: str) -> None:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise RuntimeError("ffmpeg não instalado") from e
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2000:]
        raise RuntimeError(f"Falha ao {contexto}:\n{err}")
