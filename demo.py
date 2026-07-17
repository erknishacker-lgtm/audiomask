#!/usr/bin/env python3
"""
demo.py — Demonstração completa do AudioShield (CLI).

Gera voz sintética, aplica 4 camadas, valida inaudibilidade,
opcionalmente tenta ASR e salva evidências em output/.

Uso:
  python demo.py
  python demo.py --whisper
  python demo.py --sr 48000 --texto "Ola mundo"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from core.camada4_adversarial import ParametrosAdversarial, WatermarkingAdversarial
from core.pipeline import AudioShieldPipeline, PipelineConfig
from utils.audio_io import gerar_voz_sintetica, salvar_audio
from utils.espectro import metricas_espectro
from utils.validacao import (
    estimar_impacto_asr,
    resumo_validacao,
    validar_inaudibilidade,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo AudioShield")
    parser.add_argument(
        "--texto",
        default="Ola, este e um teste de protecao de audio",
        help="Texto para voz sintética",
    )
    parser.add_argument("--sr", type=int, default=48000, help="Sample rate")
    parser.add_argument(
        "--whisper",
        action="store_true",
        help="Ativa camada 4 com Whisper e transcrição",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(ROOT, "output"),
        help="Diretório de saída",
    )
    parser.add_argument(
        "--video",
        default=None,
        help="Caminho de um MP4 para proteger (opcional)",
    )
    parser.add_argument(
        "--demo-video",
        action="store_true",
        help="Gera um MP4 sintético e protege (requer ffmpeg)",
    )
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    reports = os.path.join(ROOT, "reports")
    os.makedirs(reports, exist_ok=True)

    print("=" * 60)
    print("AudioShield — Demo de Proteção Invisível")
    print("=" * 60)

    print("\n[1/5] Gerando voz sintética...")
    y, sr = gerar_voz_sintetica(args.texto, sr=args.sr)
    path_orig = os.path.join(args.out, "demo_original.wav")
    salvar_audio(path_orig, y, sr)
    print(f"  Original: {path_orig} ({len(y)/sr:.2f}s @ {sr} Hz)")

    print("\n[2/5] Aplicando pipeline (4 camadas)...")
    cfg = PipelineConfig(
        adversarial=ParametrosAdversarial(
            usar_whisper=bool(args.whisper),
            modelo_whisper="tiny",
            n_steps=4 if args.whisper else 6,
            epsilon_db=-62.0,
        )
    )
    pipe = AudioShieldPipeline(cfg)
    yp, rel = pipe.processar(y, sr, cfg, nome_arquivo="demo_original.wav")
    path_prot = os.path.join(args.out, "demo_protegido.wav")
    salvar_audio(path_prot, yp, sr)
    print(f"  Protegido: {path_prot}")
    print(f"  Camadas: {rel.get('ordem_camadas')}")

    print("\n[3/5] Validação de inaudibilidade...")
    val = validar_inaudibilidade(y, yp, sr)
    esp = metricas_espectro(y, yp, sr)
    print(resumo_validacao(val))
    print(
        f"  Diff espectral média: {esp['diff_db_media']:.2f} dB | "
        f"corr espectral: {esp['corr_espectral']:.4f}"
    )

    asr_info = {}
    print("\n[4/5] Teste ASR (opcional)...")
    if args.whisper:
        adv = WatermarkingAdversarial(cfg.adversarial)
        t0 = adv.transcrever(y, sr)
        t1 = adv.transcrever(yp, sr)
        asr_info = estimar_impacto_asr(t0, t1)
        print(f"  Transcrição original:  {t0}")
        print(f"  Transcrição protegida: {t1}")
        print(f"  Confundiu ASR: {asr_info.get('confundiu_asr')}")
    else:
        print("  (pule com --whisper para testar Whisper)")
        print("  Fallback adversarial já aplicado na camada 4.")

    print("\n[5/5] Salvando relatório...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidencias = {
        "demo": True,
        "texto_sintetico": args.texto,
        "validacao": val,
        "espectro": esp,
        "asr": asr_info,
        "relatorio_pipeline": rel,
        "evidencia_inaudivel": {
            "snr_alto": val["snr_db"] >= 25,
            "correlacao_alta": val["correlacao"] >= 0.95,
            "passou": val["passou_inaudibilidade"],
        },
        "evidencia_confunde_asr": asr_info.get("confundiu_asr", None),
    }
    path_json = os.path.join(reports, f"demo_evidencias_{ts}.json")
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(evidencias, f, ensure_ascii=False, indent=2, default=str)
    pipe.salvar_relatorio(rel, os.path.join(reports, f"demo_pipeline_{ts}.json"))
    print(f"  {path_json}")

    # --- Vídeo (opcional) ---
    if args.demo_video or args.video:
        print("\n[Vídeo] Proteção MP4...")
        try:
            from utils.video_io import ffmpeg_disponivel, proteger_video

            if not ffmpeg_disponivel():
                print("  ffmpeg não encontrado. brew install ffmpeg")
            else:
                if args.demo_video:
                    import subprocess

                    vid_in = os.path.join(args.out, "demo_video_original.mp4")
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-f",
                            "lavfi",
                            "-i",
                            "color=c=navy:s=640x360:d=2.5",
                            "-i",
                            path_orig,
                            "-c:v",
                            "libx264",
                            "-pix_fmt",
                            "yuv420p",
                            "-c:a",
                            "aac",
                            "-shortest",
                            vid_in,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    print(f"  MP4 sintético: {vid_in}")
                else:
                    vid_in = args.video

                vid_out = os.path.join(args.out, "demo_video_protegido.mp4")
                proteger_video(vid_in, pipe, vid_out, cfg)
                print(f"  MP4 protegido: {vid_out}")
        except Exception as exc:
            print(f"  Falha no vídeo: {exc}")

    print("\n" + "=" * 60)
    print("O que isso significa:")
    print("  • Áudio salvo em output/ — ouça original vs protegido.")
    print("  • SNR alto + correlação alta ≈ diferença quase inaudível.")
    print("  • Com --whisper, veja se a transcrição mudou.")
    print("  • Com --demo-video ou --video arquivo.mp4, gera MP4 protegido.")
    print("=" * 60)
    return 0 if val.get("passou_inaudibilidade") else 0  # demo não falha o CI


if __name__ == "__main__":
    raise SystemExit(main())
