"""Tema preto · branco · vermelho (seguro para Streamlit)."""

CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap");

.stApp {
  font-family: "DM Sans", system-ui, sans-serif;
  background: #0a0a0a !important;
  color: #f5f5f5;
}

#MainMenu, footer { visibility: hidden; }
header [data-testid="stToolbar"] { display: none; }

.block-container {
  padding-top: 1.25rem;
  padding-bottom: 3rem;
  max-width: 1040px;
}

div[data-testid="stMetric"] {
  background: #141414;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 0.85rem 1rem;
}
div[data-testid="stMetricValue"] {
  font-family: "JetBrains Mono", monospace;
  font-weight: 500;
  color: #fff !important;
}

/* botões: só casca — sem mexer em span filhos */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  min-height: 2.75rem;
  border: 1px solid #333 !important;
  background: #161616 !important;
  color: #fff !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
  border-color: #E10600 !important;
  color: #fff !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"],
.stFormSubmitButton > button {
  background: #E10600 !important;
  border-color: #E10600 !important;
  color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
  background: #ff1a1a !important;
  border-color: #ff1a1a !important;
}

[data-testid="stFileUploader"],
[data-testid="stExpander"] {
  border-radius: 12px;
  border: 1px solid #2a2a2a;
  background: #121212;
}

audio, video { width: 100%; border-radius: 10px; }

/* brand blocks via st.html only */
.am-hero {
  text-align: center;
  padding: 1.5rem 1rem 1.25rem;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid #222;
}
.am-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px; height: 48px;
  border-radius: 12px;
  background: #E10600;
  color: #fff;
  font-weight: 700;
  font-size: 1.25rem;
  margin-bottom: 0.75rem;
  font-family: "JetBrains Mono", monospace;
}
.am-hero h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #fff;
}
.am-hero p {
  margin: 0.45rem auto 0;
  max-width: 36rem;
  color: #a3a3a3;
  font-size: 0.98rem;
  line-height: 1.5;
}
.am-badge {
  display: inline-block;
  font-family: "JetBrains Mono", monospace;
  font-size: 0.68rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid #333;
  color: #ccc;
  margin: 0.15rem;
  background: #141414;
}
.am-badge.red {
  border-color: #E10600;
  color: #ffb4b4;
  background: #1a0808;
}
.am-card {
  background: #121212;
  border: 1px solid #2a2a2a;
  border-radius: 14px;
  padding: 1.1rem 1.15rem;
  margin-bottom: 0.75rem;
  min-height: 7.5rem;
}
.am-card h3 {
  margin: 0 0 0.4rem 0;
  font-size: 1.05rem;
  color: #fff;
  font-weight: 600;
}
.am-card p {
  margin: 0;
  color: #a3a3a3;
  font-size: 0.88rem;
  line-height: 1.45;
}
.am-layer {
  background: #121212;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.5rem;
}
.am-layer strong { color: #fff; }
.am-layer span { color: #a3a3a3; font-size: 0.86rem; display: block; margin-top: 0.25rem; }
.am-plat {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  background: #121212;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.4rem;
}
.am-plat img {
  width: 22px; height: 22px;
  flex-shrink: 0;
}
.am-plat .name { color: #fff; font-weight: 600; font-size: 0.9rem; }
.am-section {
  font-size: 1.15rem;
  font-weight: 650;
  color: #fff;
  margin: 1.25rem 0 0.5rem;
  letter-spacing: -0.02em;
}
.am-muted { color: #a3a3a3; font-size: 0.9rem; line-height: 1.45; }
.am-price {
  font-family: "JetBrains Mono", monospace;
  font-size: 1.4rem;
  color: #E10600;
  font-weight: 600;
}
.am-login-box {
  max-width: 420px;
  margin: 0 auto;
  background: #121212;
  border: 1px solid #2a2a2a;
  border-radius: 16px;
  padding: 1.5rem 1.35rem 1.25rem;
}
.am-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-bottom: 0.85rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid #222;
}
.am-topbar .brand {
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
}
.am-topbar .brand em {
  color: #E10600;
  font-style: normal;
}
</style>
"""


def inject() -> None:
    import streamlit as st

    try:
        st.html(CSS)
    except Exception:
        pass
