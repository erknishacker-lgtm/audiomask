"""
Otimizador dual-layer com verificação STT.

Loop (auto / white-win):
  1. Gera áudio dual-layer com parâmetros
  2. Transcreve com Whisper
  3. Compara com black_text / white_text
  4. Se não passou, ajusta (mais white na banda STT / scramble black) e repete

Loop (anti_analise):
  1. Gera black + white mascarada + micro-scramble
  2. Transcreve com Whisper (proxy de robô de ads)
  3. Score de CONFUSão (black suja / misturada), não exige white 100%
  4. Prefere melhor confusão mantendo corr_vs_black alta
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.cloaker import CloakParams, aplicar_cloaker, gerar_decoy_sintetico
from core.stt_verify import STTEngine, score_anti_analise, score_dual_layer


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
    # goal: white_win (auto clássico) | anti_analise
    goal: str = "white_win"
    # anti_analise: white um degrau mais presente
    anti_decoy_db: float = -30.0
    micro_scramble_start: float = 0.10


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
    Se config.goal == anti_analise, delega ao loop de confusão.
    """
    cfg = config or OptimizeConfig()
    if (cfg.goal or "white_win").lower() in (
        "anti_analise",
        "anti-analise",
        "anti_analysis",
        "ads",
    ):
        return optimize_anti_analise(
            black_audio,
            sr,
            white_text,
            white_audio=white_audio,
            black_text_hint=black_text_hint,
            config=cfg,
        )

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
        "goal": "white_win",
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


def optimize_anti_analise(
    black_audio: np.ndarray,
    sr: int,
    white_text: str,
    *,
    white_audio: Optional[np.ndarray] = None,
    black_text_hint: str = "",
    config: Optional[OptimizeConfig] = None,
) -> OptimizeResult:
    """
    Loop focado em confusão do extrator de áudio (proxy de robô de ads).

    Não exige white vencer. Prefere: confusion alta + corr_vs_black alta.
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

    base_db = float(cfg.anti_decoy_db if cfg.anti_decoy_db else -30.0)
    if base_db <= -38:
        base_db = -30.0
    micro0 = float(cfg.micro_scramble_start or 0.10)

    # grade suave: sobe white e micro-scramble sem ir para redirect destrutivo
    schedules: List[CloakParams] = []
    db_steps = [base_db, base_db + 2.0, base_db + 4.0, base_db - 2.0, base_db + 6.0]
    for i, db in enumerate(db_steps[: max(1, cfg.max_attempts)]):
        schedules.append(
            CloakParams(
                mode="anti_analise",
                decoy_db=float(np.clip(db, -36.0, -24.0)),
                micro_scramble=min(0.22, micro0 + i * 0.03),
                mask_under_speech=min(0.95, 0.80 + i * 0.03),
                max_peak_ratio=0.07 + i * 0.01,
                seed=31 + i,
            )
        )

    attempts: List[Dict[str, Any]] = []
    best_audio = y
    best_meta: Dict[str, Any] = {}
    best_rank = -999.0
    best_transcript = ""
    best_winner = "black"
    passed = False
    best_score: Dict[str, Any] = {}

    for idx, params in enumerate(schedules[: cfg.max_attempts]):
        audio, cmeta = aplicar_cloaker(y, white_audio, sr, params)
        corr = float(cmeta.get("corr_vs_black") or 0.0)
        entry: Dict[str, Any] = {
            "attempt": idx + 1,
            "params": {
                "mode": params.mode,
                "decoy_db": params.decoy_db,
                "micro_scramble": params.micro_scramble,
                "mask_under_speech": params.mask_under_speech,
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
                score = score_anti_analise(
                    transcript, black_txt, white_txt, corr_vs_black=corr
                )
                entry["score"] = score
            else:
                entry["stt_error"] = stt.detail
        else:
            entry["stt_ok"] = False
            entry["stt_error"] = "Whisper não instalado no servidor"
            # sem STT: rank por “presença controlada” (corr alta + mode anti)
            score = {
                "passed": corr >= 0.92,
                "confusion_score": 0.15 if corr >= 0.92 else 0.0,
                "winner": "unknown",
                "black_score": 0.0,
                "white_score": 0.0,
                "quality_ok": corr >= 0.88,
                "corr_vs_black": corr,
            }
            entry["score"] = score

        attempts.append(entry)

        conf = float(score.get("confusion_score") or 0.0)
        # rank: confusão + bônus se passou + penalidade se corr cair
        rank = conf + (0.25 if score.get("passed") else 0.0) + min(corr, 1.0) * 0.35
        if corr < 0.88:
            rank -= 0.5
        if rank > best_rank:
            best_rank = rank
            best_audio = audio
            best_meta = cmeta
            best_transcript = transcript
            best_winner = str(score.get("winner") or "unknown")
            best_score = score
        if score.get("passed") and corr >= 0.90:
            passed = True
            best_audio = audio
            best_meta = cmeta
            best_transcript = transcript
            best_winner = str(score.get("winner") or "mixed")
            best_score = score
            # continua 1 tentativa a mais se houver — mas se já passou bem, pode parar
            if conf >= 0.35:
                break

    if cfg.require_stt and not stt_ok:
        passed = False

    # se nenhuma tentativa superou o original, ainda devolve melhor anti_analise
    if best_meta.get("mode") != "anti_analise" and schedules:
        best_audio, best_meta = aplicar_cloaker(y, white_audio, sr, schedules[0])

    result_meta = {
        "optimizer": "anti_analise_confusion_loop",
        "goal": "anti_analise",
        "stt_available": stt_ok,
        "passed": passed or bool(best_score.get("passed")),
        "winner": best_winner,
        "final_transcript": best_transcript,
        "white_text": white_txt,
        "black_text_hint": black_txt,
        "best_cloak": best_meta,
        "best_score": best_score,
        "attempts": attempts,
        "human_preview": "black_layer_primary",
        "ai_preview": best_transcript or "(STT indisponível — proxy de ads não rodou)",
        "honest_note": (
            "Anti-análise: mira sujar a extração de áudio (Whisper local = proxy). "
            "Não é o classificador real Meta/TikTok/Google. Não garante aprovação. "
            "Humano deve continuar ouvindo a black."
        ),
    }

    return OptimizeResult(
        audio=np.asarray(best_audio, dtype=np.float32),
        sr=sr,
        meta=result_meta,
        attempts=attempts,
        stt_available=stt_ok,
        passed=bool(result_meta["passed"]),
        final_transcript=best_transcript,
        winner=best_winner,
    )
