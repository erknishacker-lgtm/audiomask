"""Testes de suporte a vídeo MP4 (requer ffmpeg)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.pipeline import AudioShieldPipeline, PipelineConfig
from core.camada4_adversarial import ParametrosAdversarial
from utils.audio_io import gerar_voz_sintetica, salvar_audio
from utils.video_io import (
    extrair_audio_do_video,
    ffmpeg_disponivel,
    proteger_video,
    remux_audio_no_video,
)


def _gerar_mp4_teste(path: str, dur: float = 1.5, sr: int = 48000) -> None:
    """Gera MP4 sintético (cor sólida + tom) via ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=blue:s=320x240:d={dur}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={dur}:sample_rate={sr}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


@unittest.skipUnless(ffmpeg_disponivel(), "ffmpeg não instalado")
class TestVideoIO(unittest.TestCase):
    def test_extrair_e_remux(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp4_in = os.path.join(tmp, "in.mp4")
            mp4_out = os.path.join(tmp, "out.mp4")
            _gerar_mp4_teste(mp4_in)

            y, sr, meta = extrair_audio_do_video(mp4_in, sr_alvo=48000)
            self.assertGreater(len(y), 1000)
            self.assertEqual(sr, 48000)
            self.assertTrue(meta.get("video_info", {}).get("tem_audio", True) or len(y) > 0)

            # "Protege" com ruído mínimo e remux
            yp = np.clip(y + 1e-4 * np.random.randn(len(y)).astype(np.float32), -1, 1)
            remux_audio_no_video(mp4_in, yp, sr, mp4_out)
            self.assertTrue(os.path.isfile(mp4_out))
            self.assertGreater(os.path.getsize(mp4_out), 1000)

    def test_proteger_video_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp4_in = os.path.join(tmp, "in.mp4")
            mp4_out = os.path.join(tmp, "out.mp4")
            _gerar_mp4_teste(mp4_in, dur=1.0)

            pipe = AudioShieldPipeline(
                PipelineConfig(
                    adversarial=ParametrosAdversarial(usar_whisper=False)
                )
            )
            path, rel = proteger_video(mp4_in, pipe, mp4_out)
            self.assertEqual(path, mp4_out)
            self.assertTrue(os.path.isfile(mp4_out))
            self.assertIn("video", rel)
            self.assertEqual(len(rel.get("ordem_camadas", [])), 4)


if __name__ == "__main__":
    unittest.main()
