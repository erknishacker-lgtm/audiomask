"""
Pipeline MASK.SOUND v2 — funções principais.

1. Proteger áudio contra IA (cloaker black/white + anti-legenda leve)
2. Limpar metadados
3. Phase-stereo avançado
4. Compressão de vídeo perceptiva
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import numpy as np

from core.camada4_adversarial import ParametrosAdversarial, WatermarkingAdversarial
from core.cloaker import CloakParams, aplicar_cloaker, gerar_decoy_sintetico
from core.dual_layer_optimizer import OptimizeConfig, optimize_dual_layer
from core.phase_stereo import (
    PhaseStereoParams,
    encode_mid_side_cloak,
    mono_para_stereo_protegido,
)
from utils.audio_io import salvar_audio
from utils.metadata import limpar_metadados
from utils.video_compress import comprimir_video
from utils.video_io import remux_audio_no_video


# Texto white padrão (pode ser sobrescrito pelo usuário)
WHITE_COPY_DEFAULT = (
    "Oferta especial por tempo limitado. Confira as condicoes oficiais no site. "
    "Produto de qualidade com garantia e suporte ao cliente. "
    "Aproveite as condicoes de pagamento e frete conforme regulamento."
)


@dataclass
class OpcoesProcessamento:
    """Opções do popup principal."""

    proteger_audio_ia: bool = True
    limpar_metadados: bool = True
    phase_stereo: bool = True
    comprimir_video: bool = True
    usar_cloaker: bool = True
    decoy_db: float = -40.0
    white_text: str = WHITE_COPY_DEFAULT
    black_text_hint: str = ""  # copy black para o score STT
    anti_ia_leve: bool = False
    # auto | natural | white_only | redirect | anti_analise
    cloak_mode: str = "auto"
    stt_blend: float = 0.4
    black_scramble: float = 0.2
    optimize_stt: bool = True
    stt_max_attempts: int = 5
    platform: str = "capcut"
    # anti_analise defaults (ref. mercado secondary ~−22 dB)
    micro_scramble: float = 0.08
    anti_decoy_db: float = -22.0
    white_language: str = "pt"  # pt | en | es — idioma do TTS white


def processar_midia(
    audio_principal: np.ndarray,
    sr: int,
    *,
    audio_white: Optional[np.ndarray] = None,
    caminho_video: Optional[str] = None,
    out_dir: str,
    basename: str,
    opcoes: Optional[OpcoesProcessamento] = None,
) -> Dict[str, Any]:
    """
    Processa áudio (e vídeo se houver) conforme opções.

    Returns:
        dict com paths, report, audio final
    """
    opt = opcoes or OpcoesProcessamento()
    os.makedirs(out_dir, exist_ok=True)
    report: Dict[str, Any] = {"opcoes": opt.__dict__.copy(), "etapas": []}

    y = np.asarray(audio_principal, dtype=np.float32)
    if y.ndim > 1:
        y = np.mean(y, axis=0 if y.shape[0] <= 8 else 1).astype(np.float32)

    # 1) Dual-layer + otimizador STT (quando auto)
    white_src = audio_white
    tts_meta: Dict[str, Any] = {"source": "upload" if audio_white is not None else None}
    if white_src is None and opt.usar_cloaker:
        # TTS real da copy white (não formantes/barulho)
        try:
            from core.tts_white import gerar_fala_white

            white_src, tts_meta = gerar_fala_white(
                opt.white_text,
                sr,
                duracao_s=len(y) / float(sr),
                language=getattr(opt, "white_language", "pt") or "pt",
            )
            report["etapas"].append({"white_tts": tts_meta})
            if not tts_meta.get("tts"):
                report["etapas"].append(
                    {
                        "white_tts_warning": (
                            "TTS real indisponível no servidor — voz pode soar artificial. "
                            "Instale: pip install edge-tts"
                        )
                    }
                )
        except Exception as e:
            white_src = gerar_decoy_sintetico(
                opt.white_text,
                sr,
                duracao_s=len(y) / float(sr),
                language=getattr(opt, "white_language", "pt") or "pt",
            )
            tts_meta = {"error": str(e), "fallback": True, "tts": False}
            report["etapas"].append({"white_tts": tts_meta})

    # Preview isolado da white (para o usuário ouvir a voz da copy)
    white_preview_path = None
    if white_src is not None and opt.usar_cloaker:
        white_preview_path = os.path.join(out_dir, f"{basename}_white_preview.wav")
        try:
            salvar_audio(white_preview_path, white_src, sr)
            report["etapas"].append({"white_preview": os.path.basename(white_preview_path)})
        except Exception as e:
            white_preview_path = None
            report["etapas"].append({"white_preview_error": str(e)})

    stt_preview: Dict[str, Any] = {}
    mode = (getattr(opt, "cloak_mode", "auto") or "auto").lower().replace("-", "_")
    if mode in ("ads", "anti_analysis"):
        mode = "anti_analise"

    if opt.proteger_audio_ia and opt.usar_cloaker and white_src is not None:
        if mode == "anti_analise":
            # Loop de confusão (proxy robô de ads) — não exige white 100%
            opt_res = optimize_dual_layer(
                y,
                sr,
                opt.white_text or WHITE_COPY_DEFAULT,
                white_audio=white_src,
                black_text_hint=getattr(opt, "black_text_hint", "") or "",
                config=OptimizeConfig(
                    max_attempts=int(getattr(opt, "stt_max_attempts", 5) or 5),
                    decoy_db=opt.decoy_db,
                    anti_decoy_db=float(getattr(opt, "anti_decoy_db", -22.0) or -22.0),
                    micro_scramble_start=float(getattr(opt, "micro_scramble", 0.08) or 0.08),
                    language="pt",
                    whisper_model="tiny",
                    goal="anti_analise",
                    white_language=getattr(opt, "white_language", "pt") or "pt",
                ),
            )
            y_work = opt_res.audio
            report["etapas"].append({"cloaker_optimizer": opt_res.meta})
            stt_preview = {
                "stt_available": opt_res.stt_available,
                "passed": opt_res.passed,
                "winner": opt_res.winner,
                "goal": "anti_analise",
                "ai_heard": opt_res.final_transcript,
                "white_text": opt.white_text,
                "black_text_hint": getattr(opt, "black_text_hint", "") or "",
                "attempts": len(opt_res.attempts),
                "best_score": opt_res.meta.get("best_score"),
                "honest_note": opt_res.meta.get("honest_note"),
            }
            # anti_analise: metadados e phase-stereo reforçados no pacote
            if not opt.limpar_metadados:
                opt.limpar_metadados = True
                report["etapas"].append(
                    {"metadados_forcado": "anti_analise_ativa_limpeza"}
                )
        elif mode in ("auto", "optimize") or (
            getattr(opt, "optimize_stt", False) and mode not in (
                "natural", "redirect", "white_only", "anti_analise"
            )
        ):
            # Loop clássico: gera → Whisper → white vencer black
            opt_res = optimize_dual_layer(
                y,
                sr,
                opt.white_text or WHITE_COPY_DEFAULT,
                white_audio=white_src,
                black_text_hint=getattr(opt, "black_text_hint", "") or "",
                config=OptimizeConfig(
                    max_attempts=int(getattr(opt, "stt_max_attempts", 5) or 5),
                    decoy_db=opt.decoy_db,
                    language="pt",
                    whisper_model="tiny",
                    goal="white_win",
                ),
            )
            y_work = opt_res.audio
            report["etapas"].append({"cloaker_optimizer": opt_res.meta})
            stt_preview = {
                "stt_available": opt_res.stt_available,
                "passed": opt_res.passed,
                "winner": opt_res.winner,
                "goal": "white_win",
                "ai_heard": opt_res.final_transcript,
                "white_text": opt.white_text,
                "black_text_hint": getattr(opt, "black_text_hint", "") or "",
                "attempts": len(opt_res.attempts),
                "honest_note": opt_res.meta.get("honest_note"),
            }
        else:
            fixed_mode = (
                mode
                if mode in ("natural", "redirect", "white_only", "anti_analise")
                else "natural"
            )
            y_mix, meta_c = aplicar_cloaker(
                y,
                white_src,
                sr,
                CloakParams(
                    mode=fixed_mode,
                    decoy_db=(
                        float(getattr(opt, "anti_decoy_db", -22.0) or -22.0)
                        if fixed_mode == "anti_analise"
                        else opt.decoy_db
                    ),
                    stt_blend=getattr(opt, "stt_blend", 0.4),
                    black_scramble=getattr(opt, "black_scramble", 0.2),
                    micro_scramble=float(getattr(opt, "micro_scramble", 0.12) or 0.12),
                ),
            )
            report["etapas"].append({"cloaker": meta_c})
            y_work = y_mix
            stt_preview = {
                "stt_available": False,
                "passed": fixed_mode == "white_only",
                "winner": "white" if fixed_mode == "white_only" else "black",
                "goal": fixed_mode,
                "ai_heard": "",
                "note": f"modo fixo={fixed_mode} (sem loop STT)",
            }
    else:
        y_work = y
        report["etapas"].append({"cloaker": False})

    # Anti-IA leve na mistura (stealth) — não usa aggressive
    if opt.proteger_audio_ia and opt.anti_ia_leve:
        adv = WatermarkingAdversarial(
            ParametrosAdversarial(forca="stealth", usar_whisper=False)
        )
        y_work, meta_a = adv.aplicar(y_work, sr)
        report["etapas"].append({"anti_ia_leve": meta_a})
    else:
        report["etapas"].append({"anti_ia_leve": False})

    # 3) Phase-stereo / mid-side invert (igual arquivo pago *_shielded.mp4)
    audio_out_path = os.path.join(out_dir, f"{basename}.wav")
    stereo = None
    # TRUQUE DO MERCADO (TikTok mono):
    #   L = black + white,  R = -black + white
    #   mono (L+R)/2 ≈ white  → robô ouve a copy white
    #   estéreo side ≈ black  → humano ouve o anúncio
    use_ms_invert = (
        opt.phase_stereo
        and white_src is not None
        and mode in ("anti_analise", "auto", "redirect", "natural")
        and mode != "white_only"
    )
    if use_ms_invert:
        # black limpa = original do criativo (y), não o mono misturado
        black_src = y
        w_db = float(getattr(opt, "anti_decoy_db", -22.0) or -22.0)
        if mode == "natural":
            w_db = float(opt.decoy_db or -40.0)
        stereo, meta_ps = encode_mid_side_cloak(
            black_src, white_src, sr=sr, white_db=w_db
        )
        try:
            import soundfile as sf

            # soundfile: (N, ch)
            sf.write(audio_out_path, stereo.T, sr, subtype="PCM_16")
        except Exception:
            salvar_audio(audio_out_path, y_work, sr)
        report["etapas"].append({"phase_stereo": meta_ps})
        # VÍDEO leva o ESTÉREO invertido (não mono com black!)
        audio_for_mux = stereo
    elif opt.phase_stereo and white_src is not None:
        side_db = -30.0 if mode == "anti_analise" else -34.0
        stereo, meta_ps = mono_para_stereo_protegido(
            y_work,
            payload=white_src,
            sr=sr,
            params=PhaseStereoParams(side_db=side_db, invert_side=False),
        )
        try:
            import soundfile as sf

            sf.write(audio_out_path, stereo.T, sr, subtype="PCM_16")
        except Exception:
            salvar_audio(audio_out_path, y_work, sr)
        report["etapas"].append({"phase_stereo": meta_ps})
        audio_for_mux = stereo
    else:
        salvar_audio(audio_out_path, y_work, sr)
        report["etapas"].append({"phase_stereo": False})
        audio_for_mux = y_work

    # Salva também original para compare
    orig_path = os.path.join(out_dir, f"{basename}_orig.wav")
    salvar_audio(orig_path, y, sr)

    out_mp4 = None
    if caminho_video and os.path.isfile(caminho_video):
        out_mp4 = os.path.join(out_dir, f"{basename}.mp4")
        remux_audio_no_video(caminho_video, audio_for_mux, sr, out_mp4)

        # 2) Metadados
        if opt.limpar_metadados:
            cleaned = os.path.join(out_dir, f"{basename}_clean.mp4")
            limpar_metadados(out_mp4, cleaned)
            os.replace(cleaned, out_mp4)
            report["etapas"].append({"metadados": "limpo"})
        else:
            report["etapas"].append({"metadados": False})

        # 4) Compressão
        if opt.comprimir_video:
            comp = os.path.join(out_dir, f"{basename}_comp.mp4")
            comprimir_video(out_mp4, comp, crf=20, preset="medium")
            os.replace(comp, out_mp4)
            report["etapas"].append({"compressao": "crf20"})
        else:
            report["etapas"].append({"compressao": False})

        # re-limpa meta após compress se ambos
        if opt.limpar_metadados and opt.comprimir_video:
            cleaned = os.path.join(out_dir, f"{basename}_clean2.mp4")
            try:
                limpar_metadados(out_mp4, cleaned)
                os.replace(cleaned, out_mp4)
            except Exception:
                pass

    # Se só áudio e limpar meta
    if out_mp4 is None and opt.limpar_metadados:
        # wav sem tags: regrava
        tmp = os.path.join(out_dir, f"{basename}_tmp.wav")
        salvar_audio(tmp, y_work if stereo is None else y_work, sr)
        try:
            limpar_metadados(tmp, audio_out_path)
            os.unlink(tmp)
            report["etapas"].append({"metadados_audio": True})
        except Exception:
            if os.path.isfile(tmp):
                os.replace(tmp, audio_out_path)

    report["stt_preview"] = stt_preview
    report["tts_meta"] = tts_meta
    return {
        "audio_protected": audio_out_path,
        "audio_original": orig_path,
        "audio_white_preview": white_preview_path,
        "video": out_mp4,
        "report": report,
        "stt_preview": stt_preview,
        "tts_meta": tts_meta,
        "sample_rate": sr,
    }
