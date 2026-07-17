"""
Geração de espectrogramas e gráficos antes/depois (matplotlib + plotly).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np


def gerar_espectrograma(
    audio: np.ndarray,
    sr: int,
    n_fft: int = 2048,
    hop_length: int = 512,
    db: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calcula espectrograma STFT.

    Returns:
        (S, freqs, times) — S em dB se db=True.
    """
    y = _mono(audio)
    try:
        import librosa

        S = np.abs(
            librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
        )
        if db:
            S = librosa.amplitude_to_db(S, ref=np.max)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        times = librosa.frames_to_time(
            np.arange(S.shape[1]), sr=sr, hop_length=hop_length
        )
        return S, freqs, times
    except Exception:
        # Fallback numpy
        n = len(y)
        window = np.hanning(n_fft)
        frames = []
        for start in range(0, max(1, n - n_fft), hop_length):
            frame = y[start : start + n_fft]
            if len(frame) < n_fft:
                frame = np.pad(frame, (0, n_fft - len(frame)))
            frames.append(np.abs(np.fft.rfft(frame * window)))
        if not frames:
            frames = [np.abs(np.fft.rfft(np.pad(y, (0, max(0, n_fft - n)))[:n_fft]))]
        S = np.stack(frames, axis=1)
        if db:
            S = 20.0 * np.log10(S + 1e-12)
            S = S - np.max(S)
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
        times = np.arange(S.shape[1]) * hop_length / sr
        return S, freqs, times


def figura_antes_depois(
    original: np.ndarray,
    protegido: np.ndarray,
    sr: int,
    titulo: str = "Espectrograma: Antes × Depois",
    usar_plotly: bool = True,
) -> Any:
    """
    Gera figura comparativa (Plotly se disponível, senão Matplotlib).
    """
    if usar_plotly:
        try:
            return _plotly_antes_depois(original, protegido, sr, titulo)
        except Exception:
            pass
    return _matplotlib_antes_depois(original, protegido, sr, titulo)


def figura_diferenca(
    original: np.ndarray,
    protegido: np.ndarray,
    sr: int,
) -> Any:
    """Espectrograma da diferença (proteção isolada)."""
    n = min(len(original), len(protegido))
    diff = protegido[:n] - original[:n]
    S, freqs, times = gerar_espectrograma(diff, sr)
    try:
        import plotly.graph_objects as go

        fig = go.Figure(
            data=go.Heatmap(
                z=S,
                x=times,
                y=freqs,
                colorscale="Magma",
                colorbar=dict(title="dB"),
            )
        )
        fig.update_layout(
            title="Espectrograma da diferença (só o que foi injetado/alterado)",
            xaxis_title="Tempo (s)",
            yaxis_title="Frequência (Hz)",
            height=400,
            margin=dict(l=60, r=20, t=50, b=50),
            template="plotly_dark",
            paper_bgcolor="#141414",
            plot_bgcolor="#1c1c22",
            font=dict(color="#f2f2f7"),
        )
        return fig
    except Exception:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.imshow(
            S,
            aspect="auto",
            origin="lower",
            extent=[times[0], times[-1], freqs[0], freqs[-1]],
            cmap="magma",
        )
        ax.set_title("Espectrograma da diferença")
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Frequência (Hz)")
        fig.tight_layout()
        return fig


def figura_formas_de_onda(
    original: np.ndarray,
    protegido: np.ndarray,
    sr: int,
    max_pontos: int = 4000,
) -> Any:
    """
    Compara formas de onda: original, protegido e diferença amplificada.
    A diferença é o que o ouvido tenta não ouvir (máscara / camadas).
    """
    a = _mono(original).astype(np.float64)
    b = _mono(protegido).astype(np.float64)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    diff = b - a

    # Decima para plot rápido
    step = max(1, n // max_pontos)
    t = np.arange(0, n, step) / float(sr)
    a_d, b_d, d_d = a[::step], b[::step], diff[::step]

    # Amplifica diferença só para visualização (ganho legível)
    peak_d = float(np.max(np.abs(d_d))) + 1e-12
    d_vis = d_d / peak_d * 0.85

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=(
                "Original",
                "Protegido (mascarado)",
                f"Diferença amplificada (×{1.0/peak_d:.0f}) — só a proteção",
            ),
        )
        fig.add_trace(
            go.Scatter(x=t, y=a_d, mode="lines", name="Original", line=dict(width=1, color="#a8a8b8")),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=t, y=b_d, mode="lines", name="Protegido", line=dict(width=1, color="#6b5cff")),
            row=2, col=1,
        )
        fig.add_trace(
            go.Scatter(x=t, y=d_vis, mode="lines", name="Diferença", line=dict(width=1, color="#3dd68c")),
            row=3, col=1,
        )
        fig.update_layout(
            height=520,
            showlegend=False,
            margin=dict(l=50, r=20, t=60, b=40),
            template="plotly_dark",
            paper_bgcolor="#141414",
            plot_bgcolor="#1c1c22",
            font=dict(color="#f2f2f7", size=12),
            title=dict(text="Forma de onda · original vs protegido vs diferença", x=0.01),
        )
        fig.update_xaxes(title_text="Tempo (s)", row=3, col=1)
        fig.update_yaxes(title_text="Amp", row=1, col=1)
        fig.update_yaxes(title_text="Amp", row=2, col=1)
        fig.update_yaxes(title_text="Δ amp", row=3, col=1)
        return fig
    except Exception:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(3, 1, figsize=(11, 6), sharex=True)
        axes[0].plot(t, a_d, color="#888", lw=0.8)
        axes[0].set_title("Original")
        axes[1].plot(t, b_d, color="#6b5cff", lw=0.8)
        axes[1].set_title("Protegido")
        axes[2].plot(t, d_vis, color="#3dd68c", lw=0.8)
        axes[2].set_title("Diferença amplificada")
        axes[2].set_xlabel("Tempo (s)")
        fig.tight_layout()
        return fig


def sinal_diferenca(
    original: np.ndarray, protegido: np.ndarray, ganho: float = 8.0
) -> np.ndarray:
    """
    Isola a proteção (protegido - original), amplificada para ouvir no player.
    """
    a = _mono(original).astype(np.float32)
    b = _mono(protegido).astype(np.float32)
    n = min(len(a), len(b))
    diff = (b[:n] - a[:n]) * float(ganho)
    peak = float(np.max(np.abs(diff))) + 1e-12
    if peak > 0.99:
        diff = diff * (0.99 / peak)
    return diff.astype(np.float32)


def metricas_espectro(
    original: np.ndarray, protegido: np.ndarray, sr: int
) -> Dict[str, float]:
    """Compara espectros médios (prova de 'invisibilidade' relativa)."""
    So, fo, _ = gerar_espectrograma(original, sr)
    Sp, fp, _ = gerar_espectrograma(protegido, sr)
    # Alinha shapes
    f = min(So.shape[0], Sp.shape[0])
    t = min(So.shape[1], Sp.shape[1])
    So, Sp = So[:f, :t], Sp[:f, :t]
    diff = Sp - So
    return {
        "diff_db_media": float(np.mean(np.abs(diff))),
        "diff_db_max": float(np.max(np.abs(diff))),
        "diff_db_p95": float(np.percentile(np.abs(diff), 95)),
        "corr_espectral": float(
            np.corrcoef(So.flatten(), Sp.flatten())[0, 1]
        ),
    }


def _plotly_antes_depois(
    original: np.ndarray,
    protegido: np.ndarray,
    sr: int,
    titulo: str,
) -> Any:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    So, fo, to = gerar_espectrograma(original, sr)
    Sp, fp, tp = gerar_espectrograma(protegido, sr)

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Original", "Protegido / mascarado"),
        horizontal_spacing=0.08,
    )
    fig.add_trace(
        go.Heatmap(z=So, x=to, y=fo, colorscale="Viridis", showscale=False),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Heatmap(
            z=Sp,
            x=tp,
            y=fp,
            colorscale="Viridis",
            colorbar=dict(title="dB"),
        ),
        row=1,
        col=2,
    )
    fig.update_layout(
        title=titulo,
        height=420,
        margin=dict(l=50, r=20, t=60, b=50),
        template="plotly_dark",
        paper_bgcolor="#141414",
        plot_bgcolor="#1c1c22",
        font=dict(color="#f2f2f7"),
    )
    fig.update_xaxes(title_text="Tempo (s)", row=1, col=1)
    fig.update_xaxes(title_text="Tempo (s)", row=1, col=2)
    fig.update_yaxes(title_text="Frequência (Hz)", row=1, col=1)
    fig.update_yaxes(title_text="Frequência (Hz)", row=1, col=2)
    return fig


def _matplotlib_antes_depois(
    original: np.ndarray,
    protegido: np.ndarray,
    sr: int,
    titulo: str,
) -> Any:
    import matplotlib.pyplot as plt

    So, fo, to = gerar_espectrograma(original, sr)
    Sp, fp, tp = gerar_espectrograma(protegido, sr)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for ax, S, times, freqs, name in [
        (axes[0], So, to, fo, "Original"),
        (axes[1], Sp, tp, fp, "Protegido"),
    ]:
        im = ax.imshow(
            S,
            aspect="auto",
            origin="lower",
            extent=[times[0], times[-1] if len(times) else 1, freqs[0], freqs[-1]],
            cmap="viridis",
        )
        ax.set_title(name)
        ax.set_xlabel("Tempo (s)")
    axes[0].set_ylabel("Frequência (Hz)")
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.8, label="dB")
    fig.suptitle(titulo)
    fig.tight_layout()
    return fig


def _mono(audio: np.ndarray) -> np.ndarray:
    a = np.asarray(audio, dtype=np.float32)
    if a.ndim == 2:
        a = np.mean(a, axis=0 if a.shape[0] <= 8 else 1)
    return a.flatten()
