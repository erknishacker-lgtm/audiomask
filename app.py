"""
AudioMask — proteção de áudio com login, planos e painel admin.

Conta admin padrão (altere em produção):
  e-mail: admin@audiomask.com
  senha:  Admin@AudioMask2026
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Optional

import numpy as np
import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from auth.db import PLANS, User, get_db
from core.camada4_adversarial import ParametrosAdversarial
from core.pipeline import AudioShieldPipeline, PipelineConfig
from i18n.translations import LANGS, get_lang, set_lang, t
from ui.platforms import PLATFORMS, get_platform, icon_url
from ui.styles import inject as inject_styles
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
    sinal_diferenca,
)
from utils.validacao import validar_inaudibilidade
from utils.video_io import (
    extrair_audio_de_bytes,
    ffmpeg_disponivel,
    limpar_temp,
    remux_audio_no_video,
    video_para_bytes,
)

st.set_page_config(
    page_title="AudioMask",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─── sessão ────────────────────────────────────────────────────────────────

def init_state() -> None:
    defaults = {
        "lang": "pt",
        "user_id": None,
        "page": "login",  # login | hub | encrypt | account | admin
        "encrypt_step": 1,  # 1 platform 2 upload 3 result
        "platform": None,
        "resultado": None,
        "auth_tab": "login",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    set_lang(st.session_state["lang"])


def current_user() -> Optional[User]:
    uid = st.session_state.get("user_id")
    if not uid:
        return None
    return get_db().get_by_id(int(uid))


def require_login() -> Optional[User]:
    u = current_user()
    if not u:
        st.session_state["page"] = "login"
        return None
    if not u.active:
        st.error("Conta desativada." if get_lang() == "pt" else "Account disabled.")
        st.session_state["user_id"] = None
        return None
    return u


def go(page: str) -> None:
    st.session_state["page"] = page
    if page == "encrypt":
        st.session_state["encrypt_step"] = 1
        st.session_state["resultado"] = None


# ─── chrome ────────────────────────────────────────────────────────────────

def lang_selector() -> None:
    cols = st.columns([3, 1])
    with cols[1]:
        labels = list(LANGS.values())
        keys = list(LANGS.keys())
        cur = st.session_state.get("lang", "pt")
        idx = keys.index(cur) if cur in keys else 0
        choice = st.selectbox(
            t("language"),
            labels,
            index=idx,
            key="lang_box",
            label_visibility="collapsed",
        )
        new = keys[labels.index(choice)]
        if new != cur:
            st.session_state["lang"] = new
            set_lang(new)
            st.rerun()


def topbar(user: Optional[User]) -> None:
    if user:
        left, right = st.columns([3, 2])
        with left:
            try:
                st.html(
                    f'<div class="am-topbar"><div class="brand">Audio<em>Mask</em></div></div>'
                )
            except Exception:
                st.markdown("**AudioMask**")
        with right:
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                st.caption(f"{user.name}")
            with c2:
                plan = "PRO" if user.plan == "pro" else "FREE"
                st.caption(f"{plan} · {user.videos_left} {t('left')}")
            with c3:
                if st.button(t("logout"), key="btn_logout"):
                    st.session_state["user_id"] = None
                    st.session_state["page"] = "login"
                    st.session_state["resultado"] = None
                    st.rerun()
    else:
        lang_selector()


# ─── páginas ───────────────────────────────────────────────────────────────

def page_login() -> None:
    try:
        st.html(
            f"""
            <div class="am-hero">
              <div class="am-logo">◈</div>
              <h1>{t("app_name")}</h1>
              <p>{t("tagline")}</p>
              <div>
                <span class="am-badge red">{t("free_badge")}</span>
                <span class="am-badge">{t("pro_badge")}</span>
              </div>
            </div>
            """
        )
    except Exception:
        st.title(t("app_name"))
        st.caption(t("tagline"))

    lang_selector()

    tab_l, tab_r = st.tabs([t("login"), t("register")])

    with tab_l:
        st.subheader(t("login_title"))
        st.caption(t("login_sub"))
        with st.form("form_login", clear_on_submit=False):
            email = st.text_input(t("email"), key="login_email")
            password = st.text_input(t("password"), type="password", key="login_pw")
            ok = st.form_submit_button(t("login"), type="primary", use_container_width=True)
        if ok:
            if not email or not password:
                st.warning(t("fill_fields"))
            else:
                user = get_db().authenticate(email, password)
                if user:
                    st.session_state["user_id"] = user.id
                    st.session_state["page"] = "hub"
                    st.rerun()
                else:
                    st.error(t("invalid_login"))

    with tab_r:
        st.subheader(t("register_title"))
        st.caption(t("register_sub"))
        with st.form("form_reg", clear_on_submit=False):
            name = st.text_input(t("name"), key="reg_name")
            email = st.text_input(t("email"), key="reg_email")
            password = st.text_input(t("password"), type="password", key="reg_pw")
            ok = st.form_submit_button(t("register"), type="primary", use_container_width=True)
        if ok:
            if not name or not email or not password:
                st.warning(t("fill_fields"))
            elif len(password) < 6:
                st.error(t("password_short"))
            else:
                created = get_db().create_user(email, name, password, role="user", plan="free")
                if created:
                    st.success(t("account_created"))
                else:
                    st.error(t("email_exists"))


def page_hub(user: User) -> None:
    topbar(user)
    st.markdown(f"### {t('welcome')}, {user.name}")
    st.caption(t("hub_sub"))

    m1, m2, m3 = st.columns(3)
    m1.metric(t("plan"), user.plan.upper())
    m2.metric(t("credits"), f"{user.videos_left} {t('left')}")
    m3.metric(t("used"), str(user.videos_used))

    st.markdown(f"#### {t('hub_title')}")

    c1, c2 = st.columns(2)
    with c1:
        try:
            st.html(
                f'<div class="am-card"><h3>{t("action_encrypt")}</h3>'
                f'<p>{t("action_encrypt_desc")}</p></div>'
            )
        except Exception:
            st.markdown(f"**{t('action_encrypt')}**  \n{t('action_encrypt_desc')}")
        if st.button(t("action_encrypt"), type="primary", key="hub_enc", use_container_width=True):
            go("encrypt")
            st.rerun()

    with c2:
        try:
            st.html(
                f'<div class="am-card"><h3>{t("action_account")}</h3>'
                f'<p>{t("action_account_desc")}</p></div>'
            )
        except Exception:
            st.markdown(f"**{t('action_account')}**")
        if st.button(t("action_account"), key="hub_acc", use_container_width=True):
            go("account")
            st.rerun()

    if user.role == "admin":
        st.divider()
        try:
            st.html(
                f'<div class="am-card"><h3>{t("action_admin")} · {t("admin_badge")}</h3>'
                f'<p>{t("action_admin_desc")}</p></div>'
            )
        except Exception:
            st.markdown(f"**{t('action_admin')}**")
        if st.button(t("action_admin"), key="hub_adm", use_container_width=True):
            go("admin")
            st.rerun()

    # camadas didáticas
    st.markdown(f"#### {t('layers')}")
    layers = [
        ("C1", t("layer1"), t("layer1_desc")),
        ("C2", t("layer2"), t("layer2_desc")),
        ("C3", t("layer3"), t("layer3_desc")),
        ("C4", t("layer4"), t("layer4_desc")),
    ]
    cols = st.columns(4)
    for i, (code, title, desc) in enumerate(layers):
        with cols[i]:
            try:
                st.html(
                    f'<div class="am-layer"><strong>{code} · {title}</strong>'
                    f"<span>{desc}</span></div>"
                )
            except Exception:
                st.markdown(f"**{code} {title}**  \n{desc}")


def page_account(user: User) -> None:
    topbar(user)
    if st.button(t("back"), key="acc_back"):
        go("hub")
        st.rerun()

    st.markdown(f"### {t('action_account')}")
    st.write(f"**{t('email')}:** {user.email}")
    st.write(f"**{t('plan')}:** {user.plan}")
    st.write(f"**{t('credits')}:** {user.videos_used} {t('used')} / {user.video_limit} · **{user.videos_left}** {t('left')}")

    st.divider()
    try:
        st.html(
            f'<p class="am-section">{t("upgrade_title")}</p>'
            f'<p class="am-price">R$ 49,90</p>'
            f'<p class="am-muted">{t("upgrade_desc")}</p>'
        )
    except Exception:
        st.subheader(t("upgrade_title"))
        st.caption(t("upgrade_desc"))

    if user.plan != "pro":
        if st.button(t("upgrade_cta"), type="primary", key="btn_upgrade"):
            get_db().update_user(
                user.id,
                notes=(user.notes + f"\n[pedido Pro {datetime.utcnow().isoformat()}]").strip(),
            )
            st.success(t("request_sent"))
            st.info(
                "PIX / cartão: configure o gateway depois. "
                "Enquanto isso o admin ativa o plano Pro manualmente."
                if get_lang() == "pt"
                else "Payment gateway later; admin can enable Pro manually."
            )

    st.markdown("#### Histórico" if get_lang() == "pt" else "#### History")
    logs = get_db().usage_for_user(user.id)
    if not logs:
        st.caption("—" )
    else:
        for row in logs[:20]:
            st.caption(
                f"{row.get('created_at', '')[:19]} · {row.get('kind')} · "
                f"{row.get('platform') or '—'} · {row.get('filename') or ''}"
            )


def page_admin(user: User) -> None:
    if user.role != "admin":
        st.error("Acesso negado.")
        go("hub")
        st.rerun()
        return

    topbar(user)
    if st.button(t("back"), key="adm_back"):
        go("hub")
        st.rerun()

    db = get_db()
    st.markdown(f"### {t('action_admin')}")
    stats = db.stats()
    a, b, c, d = st.columns(4)
    a.metric("Users", stats["total_users"])
    b.metric("Pro", stats["pro_users"])
    c.metric("Free", stats["free_users"])
    d.metric("Videos", stats["videos_processed"])

    st.markdown(f"#### {t('admin_users')}")
    users = db.list_users()
    for u in users:
        with st.expander(f"{u.email} · {u.plan} · {u.videos_used}/{u.video_limit}"):
            with st.form(f"edit_{u.id}"):
                name = st.text_input(t("name"), value=u.name, key=f"n_{u.id}")
                role = st.selectbox(
                    t("role"),
                    ["user", "admin"],
                    index=0 if u.role == "user" else 1,
                    key=f"r_{u.id}",
                )
                plan = st.selectbox(
                    t("plan"),
                    list(PLANS.keys()),
                    index=list(PLANS.keys()).index(u.plan) if u.plan in PLANS else 0,
                    key=f"p_{u.id}",
                )
                limit = st.number_input(
                    t("limit"), min_value=0, max_value=99999, value=int(u.video_limit), key=f"l_{u.id}"
                )
                used = st.number_input(
                    t("used"), min_value=0, max_value=99999, value=int(u.videos_used), key=f"u_{u.id}"
                )
                active = st.checkbox(t("active"), value=u.active, key=f"a_{u.id}")
                notes = st.text_area(t("notes"), value=u.notes, key=f"no_{u.id}")
                new_pw = st.text_input(
                    "Nova senha (opcional)" if get_lang() == "pt" else "New password (optional)",
                    type="password",
                    key=f"pw_{u.id}",
                )
                save = st.form_submit_button(t("save"), type="primary")
            if save:
                db.update_user(
                    u.id,
                    name=name,
                    role=role,
                    plan=plan,
                    video_limit=int(limit),
                    videos_used=int(used),
                    active=active,
                    notes=notes,
                    new_password=new_pw or None,
                )
                st.success("OK")
                st.rerun()

    st.divider()
    st.caption(
        f"Admin login: admin@audiomask.com · senha inicial no README"
        if get_lang() == "pt"
        else "Default admin: admin@audiomask.com (see README)"
    )


def page_encrypt(user: User) -> None:
    topbar(user)
    if st.button(t("back"), key="enc_back_top"):
        if st.session_state["encrypt_step"] > 1:
            st.session_state["encrypt_step"] -= 1
            st.session_state["resultado"] = None
        else:
            go("hub")
        st.rerun()

    # cota
    user = get_db().get_by_id(user.id) or user
    if not user.can_process:
        st.error(t("no_credits"))
        if st.button(t("upgrade_cta"), type="primary", key="enc_up"):
            go("account")
            st.rerun()
        return

    st.progress(
        min(1.0, st.session_state["encrypt_step"] / 3),
        text=f"Passo {st.session_state['encrypt_step']}/3"
        if get_lang() == "pt"
        else f"Step {st.session_state['encrypt_step']}/3",
    )

    step = st.session_state["encrypt_step"]

    # —— passo 1: plataforma ——
    if step == 1:
        st.markdown(f"### {t('platform_title')}")
        st.caption(t("platform_sub"))

        # grid de plataformas com logo + botão
        cols = st.columns(3)
        for i, p in enumerate(PLATFORMS):
            with cols[i % 3]:
                try:
                    st.html(
                        f'<div class="am-plat">'
                        f'<img src="{icon_url(p["icon"], "FFFFFF")}" alt="{p["name"]}" />'
                        f'<span class="name">{p["name"]}</span></div>'
                    )
                except Exception:
                    st.markdown(f"**{p['name']}**")
                if st.button(
                    p["name"],
                    key=f"plat_{p['id']}",
                    use_container_width=True,
                ):
                    st.session_state["platform"] = p["id"]
                    st.session_state["encrypt_step"] = 2
                    st.rerun()

        # dica se já tiver seleção residual
        if st.session_state.get("platform"):
            plat = get_platform(st.session_state["platform"])
            st.info(t(plat["hint_key"]))

    # —— passo 2: upload + proteger ——
    elif step == 2:
        plat = get_platform(st.session_state.get("platform") or "generic")
        try:
            st.html(
                f'<div class="am-plat" style="margin-bottom:1rem">'
                f'<img src="{icon_url(plat["icon"], "FFFFFF")}" />'
                f'<span class="name">{plat["name"]}</span></div>'
            )
        except Exception:
            st.markdown(f"**{plat['name']}**")
        st.info(t(plat["hint_key"]))

        st.markdown(f"### {t('layers')}")
        for code, title, desc in [
            ("C1", t("layer1"), t("layer1_desc")),
            ("C2", t("layer2"), t("layer2_desc")),
            ("C3", t("layer3"), t("layer3_desc")),
            ("C4", t("layer4"), t("layer4_desc")),
        ]:
            st.markdown(f"**{code} · {title}** — {desc}")

        st.markdown(f"### {t('upload')}")
        modo = st.radio(
            "Tipo",
            ["Vídeo", "Áudio", "Exemplo"] if get_lang() == "pt" else ["Video", "Audio", "Sample"],
            horizontal=True,
            key="enc_modo",
            label_visibility="collapsed",
        )
        modo_key = modo.lower()
        y = sr = None
        nome = ""
        video_path = None
        video_meta = None
        is_video = False

        if "vídeo" in modo_key or "video" in modo_key:
            if not ffmpeg_disponivel():
                st.error("ffmpeg necessário no servidor.")
            else:
                up = st.file_uploader(
                    "MP4 / MOV",
                    type=["mp4", "mov", "mkv", "webm", "m4v"],
                    key="enc_vid",
                )
                if up:
                    data = up.read()
                    old = st.session_state.get("video_temp_path")
                    if old:
                        limpar_temp(old)
                    with st.spinner("…"):
                        y, sr, video_meta, video_path = extrair_audio_de_bytes(
                            data, nome=up.name, sr_alvo=48000
                        )
                    st.session_state["video_temp_path"] = video_path
                    nome = up.name
                    is_video = True
                    st.video(data)
                    st.audio(audio_para_bytes_wav(y, sr), format="audio/wav")

        elif "áudio" in modo_key or "audio" in modo_key:
            up = st.file_uploader(
                "WAV / MP3",
                type=["wav", "mp3", "flac", "ogg"],
                key="enc_aud",
            )
            if up:
                data = up.read()
                y, sr = carregar_audio(data, sr_alvo=48000)
                nome = up.name
                st.audio(audio_para_bytes_wav(y, sr), format="audio/wav")
        else:
            sample = os.path.join(ROOT, "tests", "sample_audio.wav")
            if not os.path.isfile(sample):
                yy, ss = gerar_voz_sintetica("Ola, teste de protecao", sr=48000)
                salvar_audio(sample, yy, ss)
            y, sr = carregar_audio(sample, sr_alvo=48000)
            nome = "sample_audio.wav"
            st.audio(audio_para_bytes_wav(y, sr), format="audio/wav")

        st.caption(f"{user.videos_left} {t('left')}")

        if y is not None and sr is not None:
            if st.button(t("protect"), type="primary", use_container_width=True, key="btn_prot"):
                # recheck cota
                fresh = get_db().get_by_id(user.id)
                if not fresh or not fresh.can_process:
                    st.error(t("no_credits"))
                    return
                with st.spinner("…"):
                    try:
                        cfg = PipelineConfig(
                            adversarial=ParametrosAdversarial(usar_whisper=False)
                        )
                        # dicas por plataforma: desliga ultrassom em apps que destroem HF
                        heavy = plat["id"] in ("tiktok", "kwai", "instagram", "whatsapp", "facebook")
                        if heavy:
                            cfg.ultrassom.volume_db = -48.0
                            cfg.mascaramento.intensidade_db = -26.0
                        pipe = AudioShieldPipeline(cfg)
                        yp, rel = pipe.processar(y, sr, cfg, nome_arquivo=nome)
                        out_video = None
                        if is_video and video_path:
                            out_dir = os.path.join(ROOT, "output")
                            os.makedirs(out_dir, exist_ok=True)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            out_video = os.path.join(
                                out_dir, f"protegido_{ts}_{_stem(nome)}.mp4"
                            )
                            remux_audio_no_video(video_path, yp, sr, out_video)
                            rel["video"] = video_meta
                            rel["saida_video"] = out_video
                        rel["platform"] = plat["id"]
                        # consome crédito
                        get_db().consume_video(
                            user.id,
                            kind="video" if is_video else "audio",
                            platform=plat["id"],
                            filename=nome,
                        )
                        st.session_state["resultado"] = {
                            "y0": y,
                            "yp": yp,
                            "sr": sr,
                            "rel": rel,
                            "out_video": out_video,
                            "nome": nome,
                            "is_video": is_video,
                            "platform": plat["id"],
                        }
                        st.session_state["encrypt_step"] = 3
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                        st.code(traceback.format_exc())

    # —— passo 3: resultado ——
    else:
        res = st.session_state.get("resultado")
        if not res:
            st.session_state["encrypt_step"] = 1
            st.rerun()
            return

        st.success(t("success_protect"))
        plat = get_platform(res.get("platform") or "generic")
        st.caption(f"{plat['name']} · {res.get('nome')}")

        y0, yp, sr0 = res["y0"], res["yp"], res["sr"]
        ganho = 10.0
        diff = sinal_diferenca(y0, yp, ganho=ganho)

        st.markdown(f"### {t('compare')}")
        a, b, c = st.columns(3)
        with a:
            st.markdown(f"**{t('original')}**")
            st.audio(audio_para_bytes_wav(y0, sr0), format="audio/wav")
        with b:
            st.markdown(f"**{t('protected')}**")
            st.audio(audio_para_bytes_wav(yp, sr0), format="audio/wav")
        with c:
            st.markdown(f"**{t('diff')}**")
            st.audio(audio_para_bytes_wav(diff, sr0), format="audio/wav")

        if res.get("out_video") and os.path.isfile(res["out_video"]):
            st.video(res["out_video"])

        t1, t2, t3 = st.tabs(["Onda", "Espectro", "Δ"])
        with t1:
            try:
                st.plotly_chart(figura_formas_de_onda(y0, yp, sr0), use_container_width=True)
            except Exception:
                pass
        with t2:
            try:
                st.plotly_chart(figura_antes_depois(y0, yp, sr0), use_container_width=True)
            except Exception:
                pass
        with t3:
            try:
                st.plotly_chart(figura_diferenca(y0, yp, sr0), use_container_width=True)
            except Exception:
                pass

        val = validar_inaudibilidade(y0, yp, sr0)
        m1, m2, m3 = st.columns(3)
        m1.metric("SNR", f"{val.get('snr_db', 0):.1f} dB")
        m2.metric("Corr.", f"{val.get('correlacao', 0):.3f}")
        m3.metric("Nível", str(val.get("nivel", "—")))

        st.markdown(f"### {t('download')}")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.download_button(
                "WAV",
                data=audio_para_bytes_wav(yp, sr0),
                file_name=f"audiomask_{_stem(res['nome'])}.wav",
                mime="audio/wav",
                use_container_width=True,
                key="dl_wav",
            )
        with d2:
            try:
                st.download_button(
                    "MP3",
                    data=audio_para_bytes_mp3(yp, sr0),
                    file_name=f"audiomask_{_stem(res['nome'])}.mp3",
                    mime="audio/mpeg",
                    use_container_width=True,
                    key="dl_mp3",
                )
            except Exception:
                st.caption("MP3 —")
        with d3:
            st.download_button(
                "Diff",
                data=audio_para_bytes_wav(diff, sr0),
                file_name=f"audiomask_{_stem(res['nome'])}_diff.wav",
                mime="audio/wav",
                use_container_width=True,
                key="dl_diff",
            )
        with d4:
            st.download_button(
                "JSON",
                data=json.dumps(res["rel"], ensure_ascii=False, indent=2, default=str).encode(),
                file_name=f"audiomask_{_stem(res['nome'])}.json",
                mime="application/json",
                use_container_width=True,
                key="dl_json",
            )
        if res.get("out_video") and os.path.isfile(res["out_video"]):
            st.download_button(
                "MP4",
                data=video_para_bytes(res["out_video"]),
                file_name=f"audiomask_{_stem(res['nome'])}.mp4",
                mime="video/mp4",
                use_container_width=True,
                key="dl_mp4",
            )

        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "Novo arquivo" if get_lang() == "pt" else "New file",
                key="again",
                use_container_width=True,
            ):
                st.session_state["encrypt_step"] = 1
                st.session_state["resultado"] = None
                st.rerun()
        with c2:
            if st.button(
                "Início" if get_lang() == "pt" else "Home",
                key="home",
                use_container_width=True,
            ):
                go("hub")
                st.rerun()


def _stem(nome: str) -> str:
    return os.path.splitext(os.path.basename(nome or "file"))[0] or "file"


# ─── main ──────────────────────────────────────────────────────────────────

def main() -> None:
    init_state()
    inject_styles()
    get_db()  # seed admin

    page = st.session_state.get("page", "login")
    user = current_user()

    if page == "login" or not user:
        page_login()
        return

    user = require_login()
    if not user:
        page_login()
        return

    if page == "hub":
        page_hub(user)
    elif page == "account":
        page_account(user)
    elif page == "admin":
        page_admin(user)
    elif page == "encrypt":
        page_encrypt(user)
    else:
        page_hub(user)


if __name__ == "__main__":
    main()
