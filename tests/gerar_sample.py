#!/usr/bin/env python3
"""Gera tests/sample_audio.wav (voz sintética + senoides)."""

from __future__ import annotations

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from utils.audio_io import gerar_voz_sintetica, salvar_audio


def main() -> None:
    out = os.path.join(os.path.dirname(__file__), "sample_audio.wav")
    y, sr = gerar_voz_sintetica(
        "Ola, este e um teste de protecao",
        sr=48000,
    )
    t = np.arange(len(y)) / sr
    y = y + 0.04 * np.sin(2 * np.pi * 440 * t)
    y = y + 0.02 * np.sin(2 * np.pi * 880 * t)
    y = (y / (np.max(np.abs(y)) + 1e-12) * 0.85).astype(np.float32)
    salvar_audio(out, y, sr)
    print(f"Criado: {out} ({len(y)/sr:.2f}s @ {sr} Hz)")


if __name__ == "__main__":
    main()
