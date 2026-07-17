"""Limpeza de metadados digitais (vídeo/áudio) via ffmpeg."""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional


def limpar_metadados(caminho_in: str, caminho_out: Optional[str] = None) -> str:
    """
    Remove metadados (map_metadata -1) reescrevendo container.
    Copia streams de vídeo/áudio quando possível (sem reencode pesado).
    """
    if not os.path.isfile(caminho_in):
        raise FileNotFoundError(caminho_in)

    if caminho_out is None:
        base, ext = os.path.splitext(caminho_in)
        caminho_out = f"{base}_nometa{ext or '.mp4'}"

    # -map_metadata -1 remove metadata global
    # -map_chapters -1 remove capítulos
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        caminho_in,
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c",
        "copy",
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        caminho_out,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # fallback: reencode leve se copy falhar
        cmd2 = [
            "ffmpeg",
            "-y",
            "-i",
            caminho_in,
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            caminho_out,
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        if proc2.returncode != 0:
            raise RuntimeError(
                f"Falha ao limpar metadados:\n{proc.stderr[-1500:]}\n{proc2.stderr[-1500:]}"
            )
    return caminho_out


def limpar_metadados_inplace_safe(caminho: str) -> str:
    """Escreve em temp e substitui o arquivo original."""
    ext = os.path.splitext(caminho)[1] or ".mp4"
    fd, tmp = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        limpar_metadados(caminho, tmp)
        os.replace(tmp, caminho)
        return caminho
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
