"""
AudioShield — interface Streamlit limpa e estável.

- Tema via .streamlit/config.toml (fonte da verdade de cores)
- CSS mínimo e seguro (não mexe em span/p internos dos botões)
- Labels de botão curtos e únicos (sem texto duplicado)
- Comparação original × protegido × diferença
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.camada1_mascaramento import ParametrosMascaramento
from core.camada2_ultrassom import ParametrosUltrassom
from core.camada3_dispersor import ParametrosDispersor
from core.camada4_adversarial import ParametrosAdversarial, WatermarkingAdversarial
from core.pipeline import AudioShieldPipeline, PipelineConfig
from utils.audio_io import (
    audio_para_bytes_mp3,
    audio_para_bytes_wav,
    carregar_audio,
    gerar_voz_sintetica,
    salvar_audio,
)
from utils.espectro import (
    figura_antes_depois,
    figura_diferenca,
    figura_formas_de_onda,
    metricas_espectro,
    sinal_diferenca,
)
from utils.validacao import estimar_impacto_asr, resumo_validacao, validar_inaudibilidade
from utils.video_io import (
    eh_video,
    extrair_audio_de_bytes,
    ffmpeg_disponivel,
    limpar_temp,
    remux_audio_no_video,
    video_para_bytes,
)


st.set_page_config(
    page_title="AudioShield",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# CSS deliberadamente mínimo.
# NÃO estilizar span/p/div genéricos — isso duplica texto nos botões do Streamlit.
_CSS_SAFE = """
<style>
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap");

.stApp {
  font-family: "IBM Plex Sans", system-ui, -apple-system, sans-serif;
}

/* esconde chrome desnecessário sem esconder labels de botão */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header [data-testid="stToolbar"] { display: none; }

.block-container {
  padding-top: 1.5rem;
  padding-bottom: 3rem;
  max-width: 1080px;
}

/* métricas */
div[data-testid="stMetric"] {
  background: #18181F;
  border: 1px solid #2C2C38;
  border-radius: 12px;
  padding: 0.85rem 1rem;
}
div[data-testid="stMetricValue"] {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 500;
}

/* botões: só borda/raio — NUNCA color em filhos, NUNCA content/::before */
.stButton > button,
.stDownloadButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  min-height: 2.6rem;
}

/* uploader / expander */
[data-testid="stFileUploader"],
[data-testid="stExpander"] {
  border-radius: 12px;
}

/* players */
audio, video {
  width: 100%;
  border-radius: 10px;
}

/* cards de camada (markdown) */
.as-card {
  background: #18181F;
  border: 1px solid #2C2C38;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  margin-bottom: 0.55rem;
}
.as-card.ok { border-color: #2F6B4F; }
.as-card.fail { border-color: #6B3530; }
.as-card.muted { opacity: 0.55; }
.as-card .t {
  font-size: 0.92rem;
  font-weight: 600;
  color: #ECECF1;
  margin: 0 0 0.25rem 0;
}
.as-card .s {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.72rem;
  color: #9B9BB0;
  margin: 0;
  line-height: 1.4;
}
.as-card .badge {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.68rem;
  color: #9B9BB0;
  float: right;
}
.as-card.ok .badge { color: #3DD68C; }
.as-card.fail .badge { color: #E85D4C; }

.as-hero {
  margin: 0 0 1.25rem 0;
  padding: 0 0 1.1rem 0;
  border-bottom: 1px solid #2C2C38;
}
.as-hero h1 {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
  color: #ECECF1;
}
.as-hero p {
  margin: 0.4rem 0 0 0;
  color: #9B9BB0;
  font-size: 0.95rem;
  max-width: 54ch;
  line-height: 1.5;
}
.as-mark {
  display: inline-block;
  width: 1.65rem;
  height: 1.65rem;
  line-height: 1.65rem;
  text-align: center;
  background: #7C6CFF;
  color: #fff;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  margin-right: 0.45rem;
  vertical-align: -0.15rem;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
</style>
"""


def inject_css() -> None:
    try:
        st.html(_CSS_SAFE)
    except Exception:
        pass  # tema do config.toml ainda aplica


def card_layer(n: int, nome: str, status: str, detail: str, kind: str) -> str:
    """HTML mínimo de um card (sem botões)."""
    return (
        f'<div class="as-card {kind}">'
        f'<span class="badge">{status}</span>'
        f'<p class="t">C{n} · {nome}</p>'
        f'<p class="s">{detail}</p>'
        f"</div>"
    )


def show_layers(relatorio: Optional[Dict[str, Any]], cfg: PipelineConfig) -> None:
    specs = [
        (1, "Mascaramento", "aplicar_camada1", "formantes 2.5–3.5 kHz"),
        (2, "Ultrassom", "aplicar_camada2", "portadora ~19.5 kHz"),
        (3, "Dispersor", "aplicar_camada3", "all-pass 4ª ordem"),
        (4, "Adversarial", "aplicar_camada4", "perturbação mínima"),
    ]
    by_n: Dict[int, dict] = {}
    if relatorio:
        for c in relatorio.get("camadas") or []:
            by_n[int(c.get("camada") or 0)] = c

    cols = st.columns(4, gap="small")
    for i, (n, nome, flag, hint) in enumerate(specs):
        enabled = bool(getattr(cfg, flag, True))
        meta = by_n.get(n)

        if not enabled:
            kind, status, detail = "muted", "off", hint
        elif meta is None:
            kind, status, detail = "", "pronta", hint
        elif meta.get("aplicada"):
            kind, status = "ok", "ok"
            bits = []
            if meta.get("snr_estimado_db") is not None:
                bits.append(f"SNR {meta['snr_estimado_db']:.0f} dB")
            if meta.get("snr_db") is not None:
                bits.append(f"SNR {meta['snr_db']:.0f} dB")
            if meta.get("modo"):
                bits.append(str(meta["modo"])[:22])
            if meta.get("diff_magnitude_media_db") is not None:
                bits.append(f"Δ|H| {meta['diff_magnitude_media_db']:.1f}")
            detail = " · ".join(bits) if bits else hint
        else:
            kind, status = "fail", "erro"
            detail = str(meta.get("erro") or meta.get("aviso") or "falhou")[:70]

        with cols[i]:
            try:
                st.html(card_layer(n, nome, status, detail, kind))
            except Exception:
                st.markdown(f"**C{n} {nome}** · `{status}`  \n{detail}")


def sidebar_config() -> PipelineConfig:
    st.sidebar.markdown("## Controles")
    st.sidebar.caption("Camadas e intensidades")

    st.sidebar.markdown("#### Ativas")
    c1 = st.sidebar.checkbox("Mascaramento", True, key="cb1")
    c2 = st.sidebar.checkbox("Ultrassom", True, key="cb2")
    c3 = st.sidebar.checkbox("Dispersor de fase", True, key="cb3")
    c4 = st.sidebar.checkbox("Adversarial", True, key="cb4")

    st.sidebar.markdown("#### Mascaramento")
    fmin = st.sidebar.slider("Freq. mín (Hz)", 1500, 3000, 2500, 50, key="fmin")
    fmax = st.sidebar.slider("Freq. máx (Hz)", 2500, 5000, 3500, 50, key="fmax")
    n_tons = st.sidebar.slider("Tons", 1, 8, 3, key="tons")
    int1 = st.sidebar.slider("Intensidade (dB)", -45, -15, -28, 1, key="int1")

    st.sidebar.markdown("#### Ultrassom")
    f_ultra = st.sidebar.slider("Portadora (Hz)", 16000, 21000, 19500, 100, key="fu")
    vol_u = st.sidebar.slider("Volume (dB)", -55, -35, -45, 1, key="vu")
    cutoff = st.sidebar.slider("Cutoff (Hz)", 15000, 20000, 18000, 100, key="cut")

    st.sidebar.markdown("#### Dispersor")
    gd_min = st.sidebar.slider("Delay mín (ms)", 1.0, 10.0, 2.0, 0.5, key="gdmin")
    gd_max = st.sidebar.slider("Delay máx (ms)", 5.0, 20.0, 12.0, 0.5, key="gdmax")
    int3 = st.sidebar.slider("Mix", 0.0, 1.0, 0.85, 0.05, key="int3")

    st.sidebar.markdown("#### Adversarial")
    eps = st.sidebar.slider("Epsilon (dB)", -80, -40, -62, 1, key="eps")
    usar_w = st.sidebar.checkbox("Whisper", False, key="wsp")
    modelo = st.sidebar.selectbox("Modelo", ["tiny", "base"], 0, key="mod")
    n_steps = st.sidebar.slider("Passos", 1, 20, 6, key="stp")

    st.sidebar.markdown("#### Export")
    bitrate = st.sidebar.selectbox("Bitrate", ["128k", "192k", "256k", "320k"], 1, key="br")
    st.session_state["bitrate_audio"] = bitrate
    ganho = st.sidebar.slider("Ganho da diferença", 1.0, 20.0, 10.0, 1.0, key="gdiff")
    st.session_state["ganho_diff"] = ganho

    if ffmpeg_disponivel():
        st.sidebar.success("ffmpeg pronto")
    else:
        st.sidebar.warning("sem ffmpeg (só áudio)")

    return PipelineConfig(
        aplicar_camada1=c1,
        aplicar_camada2=c2,
        aplicar_camada3=c3,
        aplicar_camada4=c4,
        mascaramento=ParametrosMascaramento(
            freq_min_hz=float(fmin),
            freq_max_hz=float(fmax),
            n_tons=int(n_tons),
            intensidade_db=float(int1),
        ),
        ultrassom=ParametrosUltrassom(
            freq_portadora_hz=float(f_ultra),
            volume_db=float(vol_u),
            cutoff_passa_alta_hz=float(cutoff),
        ),
        dispersor=ParametrosDispersor(
            group_delay_min_ms=float(gd_min),
            group_delay_max_ms=float(gd_max),
            intensidade=float(int3),
        ),
        adversarial=ParametrosAdversarial(
            epsilon_db=float(eps),
            usar_whisper=bool(usar_w),
            modelo_whisper=str(modelo),
            n_steps=int(n_steps),
        ),
        modo_stealth_tag=True,
    )


def load_media() -> Tuple[
    Optional[np.ndarray], Optional[int], str, Optional[str], Optional[dict]
]:
    modo = st.radio(
        "Fonte",
        ["Áudio", "Vídeo", "Sintético", "Exemplo"],
        horizontal=True,
        key="fonte",
        label_visibility="collapsed",
    )

    if modo == "Áudio":
        up = st.file_uploader(
            "Arquivo de áudio",
            type=["wav", "mp3", "flac", "ogg"],
            key="file_audio",
        )
        if not up:
            return None, None, "", None, None
        data = up.read()
        y, sr = carregar_audio(data)
        if sr < 44100:
            st.warning(f"{sr} Hz → reamostrando para 48 kHz (ultrassom).")
            y, sr = carregar_audio(data, sr_alvo=48000)
        return y, sr, up.name, None, None

    if modo == "Vídeo":
        if not ffmpeg_disponivel():
            st.error("Instale ffmpeg: brew install ffmpeg")
            return None, None, "", None, None
        up = st.file_uploader(
            "Arquivo de vídeo",
            type=["mp4", "mov", "mkv", "webm", "m4v", "avi"],
            key="file_video",
        )
        if not up:
            return None, None, "", None, None
        old = st.session_state.get("video_temp_path")
        if old:
            limpar_temp(old)
        data = up.read()
        with st.spinner("Extraindo áudio…"):
            try:
                y, sr, meta, path = extrair_audio_de_bytes(
                    data, nome=up.name, sr_alvo=48000
                )
            except Exception as e:
                st.error(f"Falha no vídeo: {e}")
                return None, None, "", None, None
        if len(y) < max(1, int(sr * 0.05)):
            st.error("Sem trilha de áudio.")
            limpar_temp(path)
            return None, None, "", None, None
        st.session_state["video_temp_path"] = path
        info = meta.get("video_info") or {}
        st.caption(
            f"{up.name} · {len(y)/sr:.1f}s @ {sr} Hz"
            + (f" · {info.get('largura')}×{info.get('altura')}" if info.get("largura") else "")
        )
        st.video(data)
        return y, sr, up.name, path, meta

    if modo == "Sintético":
        texto = st.text_input(
            "Texto",
            "Ola, este e um teste de protecao de audio",
            key="sint_txt",
        )
        sr_sel = st.select_slider("Sample rate", [22050, 44100, 48000], 48000, key="sint_sr")
        # label curto — um único texto
        if st.button("Gerar", key="btn_gerar", use_container_width=False):
            y, sr = gerar_voz_sintetica(texto, sr=int(sr_sel))
            st.session_state["sintetico"] = (y, sr, "voz_sintetica.wav")
        if "sintetico" in st.session_state:
            y, sr, nome = st.session_state["sintetico"]
            return y, sr, nome, None, None
        return None, None, "", None, None

    sample = os.path.join(ROOT, "tests", "sample_audio.wav")
    if not os.path.isfile(sample):
        y, sr = gerar_voz_sintetica("Ola, este e um teste de protecao", sr=48000)
        salvar_audio(sample, y, sr)
    y, sr = carregar_audio(sample)
    if sr < 44100:
        y, sr = carregar_audio(sample, sr_alvo=48000)
    return y, sr, "sample_audio.wav", None, None


def main() -> None:
    inject_css()

    try:
        st.html(
            '<div class="as-hero">'
            '<h1><span class="as-mark">◈</span>AudioShield</h1>'
            "<p>Proteção invisível em 4 camadas. Mesmo motor para áudio e trilha de vídeo. "
            "Compare original, mascarado e a diferença amplificada.</p>"
            "</div>"
        )
    except Exception:
        st.title("AudioShield")
        st.caption("Proteção invisível de áudio · 4 camadas")

    cfg = sidebar_config()

    st.markdown("### Camadas")
    show_layers(None, cfg)

    st.markdown("### Entrada")
    y, sr, nome, video_path, video_meta = load_media()

    with st.expander("Lote"):
        ups = st.file_uploader(
            "Vários arquivos",
            type=["wav", "mp3", "mp4", "mov", "mkv", "webm", "m4v"],
            accept_multiple_files=True,
            key="batch",
        )
        # label curto e único
        if st.button("Rodar lote", key="btn_lote") and ups:
            _batch(list(ups), cfg)

    if y is None or sr is None:
        st.info("Escolha uma fonte acima para começar.")
        return

    is_video = bool(video_path and os.path.isfile(video_path))

    st.markdown("### Original")
    st.audio(audio_para_bytes_wav(y, sr), format="audio/wav")
    st.caption(f"{nome} · {sr} Hz · {len(y)/sr:.2f}s" + (" · vídeo" if is_video else ""))

    pipe = AudioShieldPipeline(cfg)
    if pipe.detectar_stealth(y, sr):
        st.warning("Indício de proteção anterior (ultrassom).")

    st.markdown("### Processar")
    # UM texto só no botão
    go = st.button("Proteger", type="primary", use_container_width=True, key="btn_prot")

    if go:
        with st.spinner("Processando…"):
            try:
                yp, rel = pipe.processar(y, sr, cfg, nome_arquivo=nome)
                out_video = None
                if is_video:
                    out_dir = os.path.join(ROOT, "output")
                    os.makedirs(out_dir, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_video = os.path.join(
                        out_dir, f"protegido_{ts}_{_stem(nome)}.mp4"
                    )
                    remux_audio_no_video(
                        video_path,
                        yp,
                        sr,
                        out_video,
                        bitrate_audio=st.session_state.get("bitrate_audio", "192k"),
                    )
                    rel["video"] = video_meta
                    rel["saida_video"] = out_video
                st.session_state["resultado"] = {
                    "yp": yp,
                    "rel": rel,
                    "y0": y.copy(),
                    "sr0": sr,
                    "out_video": out_video,
                    "is_video": is_video,
                    "nome": nome,
                }
            except Exception as e:
                st.error(str(e))
                st.code(traceback.format_exc())
                return

    res = st.session_state.get("resultado")
    if not res:
        st.caption("Clique em **Proteger** para comparar.")
        return

    yp, rel = res["yp"], res["rel"]
    y0, sr0 = res["y0"], res["sr0"]
    out_video = res.get("out_video")
    is_video_res = res.get("is_video", False)
    nome_res = res.get("nome", nome)

    st.markdown("### Status")
    show_layers(rel, cfg)
    n_ok = sum(1 for c in rel.get("camadas", []) if c.get("aplicada"))
    st.caption(
        f"{n_ok} camadas ok · max |diff| {rel.get('metricas', {}).get('max_abs_diff', 0):.4f}"
    )

    st.markdown("### Comparar")
    ganho = float(st.session_state.get("ganho_diff", 10.0))
    diff = sinal_diferenca(y0, yp, ganho=ganho)

    a, b, c = st.columns(3)
    with a:
        st.markdown("**Original**")
        st.audio(audio_para_bytes_wav(y0, sr0), format="audio/wav")
    with b:
        st.markdown("**Protegido**")
        st.audio(audio_para_bytes_wav(yp, sr0), format="audio/wav")
    with c:
        st.markdown(f"**Diferença ×{ganho:.0f}**")
        st.audio(audio_para_bytes_wav(diff, sr0), format="audio/wav")

    if is_video_res and out_video and os.path.isfile(out_video):
        st.markdown("**Vídeo protegido**")
        st.video(out_video)

    t1, t2, t3 = st.tabs(["Onda", "Espectro", "Só diferença"])
    with t1:
        try:
            st.plotly_chart(figura_formas_de_onda(y0, yp, sr0), use_container_width=True)
        except Exception as e:
            st.caption(f"Onda: {e}")
    with t2:
        try:
            st.plotly_chart(figura_antes_depois(y0, yp, sr0), use_container_width=True)
        except Exception:
            try:
                st.pyplot(figura_antes_depois(y0, yp, sr0, usar_plotly=False))
            except Exception as e:
                st.caption(f"Espectro: {e}")
    with t3:
        try:
            st.plotly_chart(figura_diferenca(y0, yp, sr0), use_container_width=True)
        except Exception as e:
            st.caption(f"Diff: {e}")

    st.markdown("### Métricas")
    val = validar_inaudibilidade(y0, yp, sr0)
    esp = metricas_espectro(y0, yp, sr0)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SNR", f"{val.get('snr_db', 0):.1f} dB")
    m2.metric("Corr. tempo", f"{val.get('correlacao', 0):.3f}")
    m3.metric("Corr. espectro", f"{val.get('correlacao_espectral', esp.get('corr_espectral', 0)):.3f}")
    m4.metric("Nível", str(val.get("nivel", "—")))
    st.code(resumo_validacao(val), language=None)

    with st.expander("JSON"):
        st.json(rel)

    if st.checkbox("ASR Whisper", key="asr"):
        with st.spinner("Transcrevendo…"):
            adv = WatermarkingAdversarial(cfg.adversarial)
            t0 = adv.transcrever(y0, sr0)
            t1 = adv.transcrever(yp, sr0)
        st.write("Original:", t0 or "—")
        st.write("Protegido:", t1 or "—")
        st.json(estimar_impacto_asr(t0, t1))

    st.markdown("### Baixar")
    br = st.session_state.get("bitrate_audio", "192k")
    d1, d2, d3, d4 = st.columns(4)

    with d1:
        st.download_button(
            label="WAV",
            data=audio_para_bytes_wav(yp, sr0),
            file_name=f"audioshield_{_stem(nome_res)}.wav",
            mime="audio/wav",
            use_container_width=True,
            key="dl_wav",
        )
    with d2:
        try:
            st.download_button(
                label="MP3",
                data=audio_para_bytes_mp3(yp, sr0, bitrate=br),
                file_name=f"audioshield_{_stem(nome_res)}.mp3",
                mime="audio/mpeg",
                use_container_width=True,
                key="dl_mp3",
            )
        except Exception:
            st.caption("MP3 off")
    with d3:
        st.download_button(
            label="Diff",
            data=audio_para_bytes_wav(diff, sr0),
            file_name=f"audioshield_{_stem(nome_res)}_diff.wav",
            mime="audio/wav",
            use_container_width=True,
            key="dl_diff",
        )
    with d4:
        st.download_button(
            label="JSON",
            data=json.dumps(rel, ensure_ascii=False, indent=2, default=str).encode(),
            file_name=f"audioshield_{_stem(nome_res)}.json",
            mime="application/json",
            use_container_width=True,
            key="dl_json",
        )

    if is_video_res and out_video and os.path.isfile(out_video):
        st.download_button(
            label="MP4",
            data=video_para_bytes(out_video),
            file_name=f"audioshield_{_stem(nome_res)}.mp4",
            mime="video/mp4",
            use_container_width=True,
            key="dl_mp4",
        )

    out_dir = os.path.join(ROOT, "output")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path_wav = os.path.join(out_dir, f"protegido_{ts}.wav")
    salvar_audio(path_wav, yp, sr0)
    pipe.salvar_relatorio(rel, os.path.join(ROOT, "reports", f"relatorio_{ts}.json"))
    st.success(f"Salvo: {path_wav}")


def _batch(ups: list, cfg: PipelineConfig) -> None:
    pipe = AudioShieldPipeline(cfg)
    out_dir = os.path.join(ROOT, "output", "batch")
    os.makedirs(out_dir, exist_ok=True)
    br = st.session_state.get("bitrate_audio", "192k")
    for up in ups:
        try:
            data = up.read()
            base = os.path.splitext(up.name)[0]
            if eh_video(up.name):
                y, sr, meta, vpath = extrair_audio_de_bytes(
                    data, nome=up.name, sr_alvo=48000
                )
                try:
                    yp, rel = pipe.processar(y, sr, cfg, nome_arquivo=up.name)
                    out_mp4 = os.path.join(out_dir, f"{base}_protegido.mp4")
                    remux_audio_no_video(vpath, yp, sr, out_mp4, bitrate_audio=br)
                    rel["video"] = meta
                    pipe.salvar_relatorio(
                        rel, os.path.join(out_dir, f"{base}_relatorio.json")
                    )
                    st.success(f"{up.name} ok")
                finally:
                    limpar_temp(vpath)
            else:
                y, sr = carregar_audio(data, sr_alvo=48000)
                yp, rel = pipe.processar(y, sr, cfg, nome_arquivo=up.name)
                salvar_audio(os.path.join(out_dir, f"{base}_protegido.wav"), yp, sr)
                pipe.salvar_relatorio(
                    rel, os.path.join(out_dir, f"{base}_relatorio.json")
                )
                st.success(f"{up.name} ok")
        except Exception as e:
            st.error(f"{up.name}: {e}")


def _stem(nome: str) -> str:
    return os.path.splitext(os.path.basename(nome or "audio"))[0] or "audio"


if __name__ == "__main__":
    main()
