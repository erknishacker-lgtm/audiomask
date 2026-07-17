"""Compressão de vídeo com qualidade perceptiva alta (CRF)."""

from __future__ import annotations

import os
import subprocess
from typing import Optional


def comprimir_video(
    caminho_in: str,
    caminho_out: Optional[str] = None,
    crf: int = 20,
    preset: str = "medium",
    audio_bitrate: str = "192k",
) -> str:
    """
    Reencode H.264 CRF (18–23 ≈ visualmente sem perda perceptível).
    """
    if not os.path.isfile(caminho_in):
        raise FileNotFoundError(caminho_in)
    if caminho_out is None:
        base, ext = os.path.splitext(caminho_in)
        caminho_out = f"{base}_compressed{ext or '.mp4'}"

    crf = int(max(16, min(28, crf)))
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        caminho_in,
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-movflags",
        "+faststart",
        caminho_out,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Compressão falhou:\n{proc.stderr[-2000:]}")
    return caminho_out
