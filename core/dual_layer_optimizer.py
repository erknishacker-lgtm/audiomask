"""
Otimizador dual-layer com verificação STT.

Loop:
  1. Gera áudio dual-layer com parâmetros
  2. Transcreve com Whisper
  3. Compara com black_text / white_text
  4. Se não passou, ajusta (mais white na banda STT / scramble black) e repete
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.cloaker import CloakParams, aplicar_cloaker, gerar_decoy_sintetico
from core.stt_verify import STTEngine, score_dual_layer


@dataclass
class OptimizeConfig:
    max_attempts: int = 5
    language: str = "pt"
    whisper_model: str = "tiny"
    # partida
    stt_blend_start: float = 0.35
    scramble_start: float = 0.15
    decoy_db: float = -38.0
    # se STT indisponível, ainda gera dual-layer natural
    require_stt: bool = False


@dataclass
class OptimizeResult:
    audio: np.ndarray
    sr: int
    meta: Dict[str, Any]
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    stt_available: bool = False
    passed: bool = False
    final_transcript: str = ""
    winner: str = "unknown"


def _black_reference_text(black_hint: str, white_text: str) -> str:
    """Texto black para score: hint do usuário ou placeholder genérico agressivo."""
    h = (black_hint or "").strip()
    if h:
        return h
    # sem texto black: usamos contraste genérico (piora precisão do score)
    return (
        "compre agora desconto imperdivel oferta exclusiva so hoje "
        "clique no link e garanta ja"
    )


def optimize_dual_layer(
    black_audio: np.ndarray,
    sr: int,
    white_text: str,
    *,
    white_audio: Optional[np.ndarray] = None,
    black_text_hint: str = "",
    config: Optional[OptimizeConfig] = None,
) -> OptimizeResult:
    """
    Produz melhor tentativa dual-layer com feedback STT.
    """
    cfg = config or OptimizeConfig()
    y = np.asarray(black_audio, dtype=np.float32).flatten()
    white_txt = (white_text or "").strip() or (
        "Oferta especial. Confira as condicoes oficiais no site. "
        "Produto com garantia e suporte ao cliente."
    )
    black_txt = _black_reference_text(black_text_hint, white_txt)

    if white_audio is None:
        white_audio = gerar_decoy_sintetico(white_txt, sr, duracao_s=len(y) / float(sr))

    engine = STTEngine(model_size=cfg.whisper_model)
    stt_ok = engine.available()

    attempts: List[Dict[str, Any]] = []
    best_audio = y
    best_meta: Dict[str, Any] = {}
    best_score_gap = -999.0
    best_transcript = ""
    best_winner = "black"
    passed = False

    blend = cfg.stt_blend_start
    scramble = cfg.scramble_start

    # Sempre começa com natural (qualidade) e depois sobe redirect se STT existir
    schedules: List[CloakParams] = []
    # tentativa 0: natural (black perfeito)
    schedules.append(
        CloakParams(mode="natural", decoy_db=cfg.decoy_db, seed=7)
    )
    if stt_ok:
        for i in range(cfg.max_attempts - 1):
            schedules.append(
                CloakParams(
                    mode="redirect",
                    decoy_db=cfg.decoy_db,
                    stt_blend=min(0.58, blend + i * 0.06),
                    black_scramble=min(0.4, scramble + i * 0.05),
                    seed=11 + i,
                )
            )
    else:
        # sem whisper: natural + um redirect leve
        schedules.append(
            CloakParams(
                mode="redirect",
                decoy_db=cfg.decoy_db,
                stt_blend=0.42,
                black_scramble=0.2,
                seed=21,
            )
        )

    for idx, params in enumerate(schedules[: cfg.max_attempts]):
        audio, cmeta = aplicar_cloaker(y, white_audio, sr, params)
        entry: Dict[str, Any] = {
            "attempt": idx + 1,
            "params": {
                "mode": params.mode,
                "stt_blend": params.stt_blend,
                "black_scramble": params.black_scramble,
                "decoy_db": params.decoy_db,
            },
            "cloak": cmeta,
        }

        transcript = ""
        score: Dict[str, Any] = {}
        if stt_ok:
            stt = engine.transcribe(audio, sr, language=cfg.language)
            entry["stt_backend"] = stt.backend
            entry["stt_ok"] = stt.ok
            if stt.ok:
                transcript = stt.text
                score = score_dual_layer(transcript, black_txt, white_txt)
                entry["score"] = score
            else:
                entry["stt_error"] = stt.detail
        else:
            entry["stt_ok"] = False
            entry["stt_error"] = "Whisper não instalado no servidor"

        attempts.append(entry)

        # ranking: prefer passed; else maior (white - black)
        gap = 0.0
        if score:
            gap = float(score["white_score"] - score["black_score"])
            if gap > best_score_gap or score.get("passed"):
                best_score_gap = gap
                best_audio = audio
                best_meta = cmeta
                best_transcript = transcript
                best_winner = score.get("winner", "unknown")
            if score.get("passed"):
                passed = True
                best_audio = audio
                best_meta = cmeta
                best_transcript = transcript
                best_winner = "white"
                break
        else:
            # sem STT: prefere natural (corr alta)
            corr = float(cmeta.get("corr_vs_black") or 0)
            if corr > best_score_gap:
                best_score_gap = corr
                best_audio = audio
                best_meta = cmeta
                best_winner = "unknown"

    # se STT obrigatório e falhou install
    if cfg.require_stt and not stt_ok:
        passed = False

    result_meta = {
        "optimizer": "dual_layer_stt_loop",
        "stt_available": stt_ok,
        "passed": passed,
        "winner": best_winner,
        "final_transcript": best_transcript,
        "white_text": white_txt,
        "black_text_hint": black_txt,
        "best_cloak": best_meta,
        "attempts": attempts,
        "human_preview": "black_layer_primary",
        "ai_preview": best_transcript or "(STT indisponível — instale openai-whisper)",
        "honest_note": (
            "Otimizado contra Whisper local (proxy de STT). "
            "Meta/TikTok Ads podem diferir. CapCut legenda forte ainda pode ler black."
        ),
    }

    return OptimizeResult(
        audio=best_audio.astype(np.float32),
        sr=sr,
        meta=result_meta,
        attempts=attempts,
        stt_available=stt_ok,
        passed=passed,
        final_transcript=best_transcript,
        winner=best_winner,
    )
