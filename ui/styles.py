"""
Tema MASK.SOUND — alinhado ao logo.

Logo: máscara escura + glow ciano/azul elétrico + waveform.
Fundo do app: cinza-carvão (como o fundo do logo), NÃO branco (logo some).
Acento: ciano #2ECBFF / azul #1A8CFF (não vermelho).
"""

from __future__ import annotations

import base64
import os
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(ROOT, "assets", "logo.png")

# Tokens (do logo)
BG = "#1B1C1E"          # carvão do fundo do logo
SURFACE = "#25262A"     # painéis
SURFACE_2 = "#2E3035"
BORDER = "#3A3C42"
INK = "#F2F4F7"
MUTED = "#9AA0A8"
CYAN = "#2ECBFF"        # olhos / glow
CYAN_DIM = "#1A8CFF"    # waveform azul
CYAN_GLOW = "rgba(46, 203, 255, 0.18)"


CSS = f"""
<style>
@import url("https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500;600&display=swap");

.stApp {{
  font-family: "DM Sans", system-ui, sans-serif;
  background: {BG} !important;
  color: {INK};
}}

#MainMenu, footer {{ visibility: hidden; }}
header [data-testid="stToolbar"] {{ display: none; }}

.block-container {{
  padding-top: 1.1rem;
  padding-bottom: 3rem;
  max-width: 1040px;
}}

div[data-testid="stMetric"] {{
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.85rem 1rem;
}}
div[data-testid="stMetricValue"] {{
  font-family: "JetBrains Mono", monospace;
  font-weight: 500;
  color: {INK} !important;
}}

/* botões — sem estilizar span filhos (evita texto duplicado) */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {{
  border-radius: 10px !important;
  font-weight: 600 !important;
  min-height: 2.75rem;
  border: 1px solid {BORDER} !important;
  background: {SURFACE_2} !important;
  color: {INK} !important;
}}
.stButton > button:hover,
.stDownloadButton > button:hover {{
  border-color: {CYAN} !important;
  box-shadow: 0 0 0 1px {CYAN_GLOW};
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {{
  background: linear-gradient(135deg, {CYAN_DIM}, {CYAN}) !important;
  border-color: transparent !important;
  color: #061018 !important;
}}
.stButton > button[kind="primary"]:hover {{
  filter: brightness(1.08);
}}

[data-testid="stFileUploader"],
[data-testid="stExpander"] {{
  border-radius: 12px;
  border: 1px solid {BORDER};
  background: {SURFACE};
}}

audio, video {{ width: 100%; border-radius: 10px; }}

/* —— brand —— */
.ms-hero {{
  text-align: center;
  padding: 0.5rem 0.5rem 1.35rem;
  margin-bottom: 1.1rem;
  border-bottom: 1px solid {BORDER};
  background:
    radial-gradient(ellipse 70% 55% at 50% 30%, {CYAN_GLOW}, transparent 70%);
}}
.ms-hero-logo {{
  width: min(220px, 55vw);
  height: auto;
  display: block;
  margin: 0 auto 0.35rem;
  filter: drop-shadow(0 0 24px rgba(46, 203, 255, 0.35));
}}
.ms-hero h1 {{
  margin: 0.15rem 0 0;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: {INK};
}}
.ms-hero h1 span {{ color: {CYAN}; }}
.ms-hero p {{
  margin: 0.5rem auto 0;
  max-width: 34rem;
  color: {MUTED};
  font-size: 0.95rem;
  line-height: 1.5;
}}
.ms-badge {{
  display: inline-block;
  font-family: "JetBrains Mono", monospace;
  font-size: 0.68rem;
  padding: 0.22rem 0.55rem;
  border-radius: 999px;
  border: 1px solid {BORDER};
  color: {MUTED};
  margin: 0.2rem;
  background: {SURFACE};
}}
.ms-badge.cyan {{
  border-color: rgba(46, 203, 255, 0.45);
  color: {CYAN};
  background: rgba(46, 203, 255, 0.08);
}}

.ms-topbar {{
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding-bottom: 0.85rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid {BORDER};
}}
.ms-topbar img {{
  width: 40px;
  height: 40px;
  border-radius: 10px;
  object-fit: cover;
  background: {SURFACE};
  box-shadow: 0 0 16px {CYAN_GLOW};
}}
.ms-topbar .brand {{
  font-weight: 700;
  letter-spacing: 0.08em;
  font-size: 0.95rem;
  color: {INK};
}}
.ms-topbar .brand span {{ color: {CYAN}; }}

.ms-card {{
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 14px;
  padding: 1.1rem 1.15rem;
  margin-bottom: 0.75rem;
  min-height: 7.2rem;
}}
.ms-card h3 {{
  margin: 0 0 0.4rem 0;
  font-size: 1.05rem;
  color: {INK};
  font-weight: 600;
}}
.ms-card p {{
  margin: 0;
  color: {MUTED};
  font-size: 0.88rem;
  line-height: 1.45;
}}

.ms-layer {{
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.5rem;
}}
.ms-layer strong {{ color: {INK}; }}
.ms-layer span {{
  color: {MUTED};
  font-size: 0.86rem;
  display: block;
  margin-top: 0.25rem;
}}

.ms-plat {{
  display: flex;
  align-items: center;
  gap: 0.55rem;
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.4rem;
}}
.ms-plat img {{ width: 22px; height: 22px; flex-shrink: 0; }}
.ms-plat .name {{ color: {INK}; font-weight: 600; font-size: 0.9rem; }}

.ms-section {{
  font-size: 1.15rem;
  font-weight: 650;
  color: {INK};
  margin: 1.25rem 0 0.5rem;
  letter-spacing: -0.02em;
}}
.ms-muted {{ color: {MUTED}; font-size: 0.9rem; line-height: 1.45; }}
.ms-price {{
  font-family: "JetBrains Mono", monospace;
  font-size: 1.4rem;
  color: {CYAN};
  font-weight: 600;
}}
.ms-login-box {{
  max-width: 420px;
  margin: 0 auto;
}}
</style>
"""


def logo_data_uri() -> Optional[str]:
    """Logo em data URI para HTML (fundo escuro do próprio PNG)."""
    if not os.path.isfile(LOGO_PATH):
        return None
    with open(LOGO_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def inject() -> None:
    import streamlit as st

    try:
        st.html(CSS)
    except Exception:
        pass


def show_logo(width: int = 200, key: str = "logo") -> None:
    """Mostra o logo com st.image (fundo do app já é escuro)."""
    import streamlit as st

    if os.path.isfile(LOGO_PATH):
        # colunas para centralizar
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown("**MASK.SOUND**")
