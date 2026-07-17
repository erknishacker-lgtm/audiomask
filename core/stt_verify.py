"""
Verificação STT (Whisper) + similaridade com black/white.

Usado pelo otimizador dual-layer: só “passa” se a transcrição
parecer mais com a copy white do que com a black (ou se a black
ficar bem degradada na leitura do modelo).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\sàáâãäéêëíóôõöúçñ]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokens(s: str) -> set:
    return {t for t in _normalize_text(s).split() if len(t) > 1}


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def overlap_ratio(ref: str, hyp: str) -> float:
    """Fração dos tokens de ref que aparecem em hyp."""
    tr, th = _tokens(ref), _tokens(hyp)
    if not tr:
        return 0.0
    return len(tr & th) / len(tr)


@dataclass
class STTResult:
    text: str
    backend: str
    ok: bool
    detail: str = ""


class STTEngine:
    """Whisper com fallbacks (openai-whisper → transformers → none)."""

    def __init__(self, model_size: str = "tiny") -> None:
        self.model_size = model_size
        self._backend: Optional[str] = None
        self._model = None
        self._pipe = None

    def available(self) -> bool:
        try:
            import whisper  # noqa: F401

            return True
        except Exception:
            try:
                import transformers  # noqa: F401

                return True
            except Exception:
                return False

    def transcribe(self, audio: np.ndarray, sr: int, language: str = "pt") -> STTResult:
        y = np.asarray(audio, dtype=np.float32).flatten()
        if sr != 16000:
            y = _resample(y, sr, 16000)
        # normaliza
        peak = float(np.max(np.abs(y)) + 1e-12)
        y = y / peak * 0.95

        # 1) openai-whisper
        try:
            import whisper

            if self._backend != "openai" or self._model is None:
                self._model = whisper.load_model(self.model_size)
                self._backend = "openai"
            r = self._model.transcribe(y, fp16=False, language=language)
            text = (r.get("text") or "").strip()
            return STTResult(text=text, backend="openai-whisper", ok=True)
        except Exception as e1:
            err1 = str(e1)

        # 2) transformers
        try:
            from transformers import pipeline

            if self._backend != "hf" or self._pipe is None:
                self._pipe = pipeline(
                    "automatic-speech-recognition",
                    model=f"openai/whisper-{self.model_size}",
                    device=-1,
                )
                self._backend = "hf"
            out = self._pipe({"array": y, "sampling_rate": 16000})
            text = (out.get("text") if isinstance(out, dict) else str(out) or "").strip()
            return STTResult(text=text, backend="transformers", ok=True)
        except Exception as e2:
            return STTResult(
                text="",
                backend="none",
                ok=False,
                detail=f"whisper={err1}; hf={e2}",
            )


def _resample(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return y.astype(np.float32)
    try:
        import librosa

        return librosa.resample(y.astype(np.float32), orig_sr=sr_in, target_sr=sr_out)
    except Exception:
        n = int(len(y) * sr_out / sr_in)
        return np.interp(
            np.linspace(0, 1, max(1, n)), np.linspace(0, 1, len(y)), y
        ).astype(np.float32)


def score_dual_layer(
    transcript: str,
    black_text: str,
    white_text: str,
) -> Dict[str, Any]:
    """
    Scores: quanto a transcrição parece white vs black.
    pass se white_score > black_score e white_score >= limiar.
    """
    tw = overlap_ratio(white_text, transcript)
    tb = overlap_ratio(black_text, transcript)
    jw = jaccard(white_text, transcript)
    jb = jaccard(black_text, transcript)
    white_score = 0.6 * tw + 0.4 * jw
    black_score = 0.6 * tb + 0.4 * jb
    # passa se white vence black com margem, ou black quase zero e white algo
    passed = (white_score >= black_score + 0.08 and white_score >= 0.12) or (
        black_score < 0.08 and white_score >= 0.15
    )
    return {
        "transcript": transcript,
        "white_score": round(white_score, 4),
        "black_score": round(black_score, 4),
        "white_overlap": round(tw, 4),
        "black_overlap": round(tb, 4),
        "passed": bool(passed),
        "winner": "white"
        if white_score > black_score
        else ("black" if black_score > white_score else "tie"),
    }
