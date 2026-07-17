"""
Leitura e escrita de áudio WAV/MP3 + gerador de voz sintética para testes.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Optional, Tuple, Union

import numpy as np


def carregar_audio(
    caminho_ou_bytes: Union[str, bytes, bytearray],
    sr_alvo: Optional[int] = None,
) -> Tuple[np.ndarray, int]:
    """
    Carrega WAV/MP3 e devolve (mono float32, sample_rate).

    Args:
        caminho_ou_bytes: caminho do arquivo ou conteúdo binário.
        sr_alvo: se definido, reamostra para esta taxa.
    """
    try:
        import soundfile as sf
    except ImportError as e:
        raise ImportError("soundfile é obrigatório: pip install soundfile") from e

    try:
        if isinstance(caminho_ou_bytes, (bytes, bytearray)):
            data = bytes(caminho_ou_bytes)
            # Tenta soundfile (WAV/FLAC/OGG)
            try:
                y, sr = sf.read(io.BytesIO(data), always_2d=False)
            except Exception:
                y, sr = _carregar_via_pydub_bytes(data)
        else:
            caminho = str(caminho_ou_bytes)
            ext = os.path.splitext(caminho)[1].lower()
            if ext == ".mp3":
                y, sr = _carregar_via_pydub_path(caminho)
            else:
                try:
                    y, sr = sf.read(caminho, always_2d=False)
                except Exception:
                    y, sr = _carregar_via_pydub_path(caminho)

        y = _para_mono_float32(y)
        sr = int(sr)

        if sr_alvo and sr_alvo != sr:
            y = _resample(y, sr, sr_alvo)
            sr = int(sr_alvo)

        # Evita clipping na entrada
        peak = float(np.max(np.abs(y))) + 1e-12
        if peak > 1.0:
            y = y / peak

        return y.astype(np.float32), sr

    except Exception as exc:
        raise RuntimeError(f"Falha ao carregar áudio: {exc}") from exc


def salvar_audio(
    caminho: str,
    audio: np.ndarray,
    sr: int,
    formato: Optional[str] = None,
    bitrate_mp3: str = "192k",
) -> str:
    """
    Salva áudio em WAV ou MP3.

    Args:
        caminho: destino (extensão define formato se `formato` for None).
        audio: sinal mono/multi.
        sr: taxa de amostragem.
        formato: 'wav' | 'mp3' | None (auto).
        bitrate_mp3: ex. '128k', '192k', '320k'.
    """
    y = _para_mono_float32(audio)
    y = np.clip(y, -1.0, 1.0)

    ext = (formato or os.path.splitext(caminho)[1].lstrip(".")).lower()
    os.makedirs(os.path.dirname(os.path.abspath(caminho)) or ".", exist_ok=True)

    if ext in ("", "wav", "wave"):
        if not caminho.lower().endswith(".wav"):
            caminho = caminho + ".wav" if ext == "" else caminho
        import soundfile as sf

        sf.write(caminho, y, sr, subtype="PCM_16")
        return caminho

    if ext == "mp3":
        return _salvar_mp3(caminho, y, sr, bitrate_mp3)

    # Fallback: WAV
    import soundfile as sf

    if not caminho.endswith(".wav"):
        caminho = os.path.splitext(caminho)[0] + ".wav"
    sf.write(caminho, y, sr, subtype="PCM_16")
    return caminho


def audio_para_bytes_wav(audio: np.ndarray, sr: int) -> bytes:
    """Serializa áudio para bytes WAV (download Streamlit)."""
    import soundfile as sf

    y = np.clip(_para_mono_float32(audio), -1.0, 1.0)
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


def audio_para_bytes_mp3(
    audio: np.ndarray, sr: int, bitrate: str = "192k"
) -> bytes:
    """Serializa áudio para bytes MP3 (requer ffmpeg via pydub)."""
    y = np.clip(_para_mono_float32(audio), -1.0, 1.0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        wav_path = tmp_wav.name
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
        mp3_path = tmp_mp3.name
    try:
        import soundfile as sf

        sf.write(wav_path, y, sr, subtype="PCM_16")
        from pydub import AudioSegment

        seg = AudioSegment.from_wav(wav_path)
        seg.export(mp3_path, format="mp3", bitrate=bitrate)
        with open(mp3_path, "rb") as f:
            return f.read()
    finally:
        for p in (wav_path, mp3_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def gerar_voz_sintetica(
    texto: str = "Ola, este e um teste de protecao",
    sr: int = 22050,
    duracao_por_char: float = 0.07,
    f0: float = 140.0,
) -> Tuple[np.ndarray, int]:
    """
    Gera áudio sintético tipo 'voz' (formantes + pitch).

    Não é TTS neural — é um sintetizador formante simples para demos/testes,
    suficiente para exercitar as 4 camadas sem dependências externas.
    """
    # Mapa grosseiro char → formantes (Hz) estilo vogal
    vogais = {
        "a": (800, 1200, 2500),
        "e": (500, 1700, 2500),
        "i": (300, 2200, 3000),
        "o": (500, 900, 2400),
        "u": (350, 700, 2300),
    }
    rng = np.random.default_rng(abs(hash(texto)) % (2**31))
    chunks = []
    t_sil = int(0.08 * sr)
    chunks.append(np.zeros(t_sil, dtype=np.float64))

    for ch in texto.lower():
        n = max(1, int(duracao_por_char * sr))
        if ch == " ":
            chunks.append(np.zeros(int(0.06 * sr)))
            continue
        if not ch.isalpha():
            continue
        forms = vogais.get(ch, (600, 1400, 2400))
        t = np.arange(n) / sr
        # Contorno de pitch leve
        pitch = f0 * (1.0 + 0.05 * np.sin(2 * np.pi * 3 * t))
        phase = 2 * np.pi * np.cumsum(pitch) / sr
        source = 0.2 * np.sin(phase) + 0.05 * rng.standard_normal(n)
        # Envelope ADSR simples
        env = np.ones(n)
        a = max(1, n // 10)
        r = max(1, n // 5)
        env[:a] = np.linspace(0, 1, a)
        env[-r:] = np.linspace(1, 0, r)
        sig = np.zeros(n)
        for i, f in enumerate(forms):
            amp = 1.0 / (i + 1)
            sig += amp * np.sin(2 * np.pi * f * t + source)
        # Mistura com source glotal
        sig = 0.7 * sig * env + 0.3 * source * env
        chunks.append(sig)

    chunks.append(np.zeros(t_sil))
    y = np.concatenate(chunks) if chunks else np.zeros(sr, dtype=np.float64)
    # Filtro leve passa-baixa anti-alias
    try:
        from scipy.signal import butter, sosfiltfilt

        sos = butter(4, min(0.45, 7000 / (sr / 2)), btype="low", output="sos")
        y = sosfiltfilt(sos, y)
    except Exception:
        pass

    peak = np.max(np.abs(y)) + 1e-12
    y = (0.8 * y / peak).astype(np.float32)
    return y, sr


def _carregar_via_pydub_path(caminho: str) -> Tuple[np.ndarray, int]:
    from pydub import AudioSegment

    seg = AudioSegment.from_file(caminho)
    return _segment_para_numpy(seg)


def _carregar_via_pydub_bytes(data: bytes) -> Tuple[np.ndarray, int]:
    from pydub import AudioSegment

    seg = AudioSegment.from_file(io.BytesIO(data))
    return _segment_para_numpy(seg)


def _segment_para_numpy(seg) -> Tuple[np.ndarray, int]:
    samples = np.array(seg.get_array_of_samples()).astype(np.float32)
    if seg.channels > 1:
        samples = samples.reshape((-1, seg.channels)).mean(axis=1)
    max_val = float(1 << (seg.sample_width * 8 - 1))
    samples = samples / max_val
    return samples.astype(np.float32), int(seg.frame_rate)


def _salvar_mp3(caminho: str, y: np.ndarray, sr: int, bitrate: str) -> str:
    if not caminho.lower().endswith(".mp3"):
        caminho = os.path.splitext(caminho)[0] + ".mp3"
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        import soundfile as sf
        from pydub import AudioSegment

        sf.write(wav_path, y, sr, subtype="PCM_16")
        seg = AudioSegment.from_wav(wav_path)
        seg.export(caminho, format="mp3", bitrate=bitrate)
        return caminho
    except Exception as exc:
        # Fallback: salva WAV e avisa
        alt = os.path.splitext(caminho)[0] + ".wav"
        import soundfile as sf

        sf.write(alt, y, sr, subtype="PCM_16")
        raise RuntimeError(
            f"MP3 falhou ({exc}). WAV salvo em {alt}. "
            "Instale ffmpeg para exportar MP3."
        ) from exc
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


def _para_mono_float32(y: np.ndarray) -> np.ndarray:
    a = np.asarray(y)
    if a.ndim == 2:
        if a.shape[0] <= 8 and a.shape[0] < a.shape[1]:
            a = np.mean(a, axis=0)
        else:
            a = np.mean(a, axis=1)
    return a.astype(np.float32).flatten()


def _resample(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    try:
        import librosa

        return librosa.resample(y.astype(np.float32), orig_sr=sr_in, target_sr=sr_out)
    except Exception:
        n_out = int(len(y) * sr_out / sr_in)
        return np.interp(
            np.linspace(0, 1, max(1, n_out)),
            np.linspace(0, 1, len(y)),
            y,
        ).astype(np.float32)
