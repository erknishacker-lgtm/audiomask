"""
Síntese de fala real para a camada white (copy falada).

Modelo desejado (referência de mercado):
  white = VOZ lendo a copy, não barulho/formantes.

Ordem de engines (VPS/Docker friendly):
  1) edge-tts em thread isolada (Microsoft neural)
  2) gTTS (Google, precisa rede) + decode ffmpeg
  3) espeak-ng / espeak (offline no container)
  4) macOS `say` (dev local)
  5) formantes — só emergência (soa artificial)
"""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple

import numpy as np


def _detect_lang(text: str, hint: str = "") -> str:
    h = (hint or "").lower().strip()
    if h.startswith("en"):
        return "en"
    if h.startswith("es") or h.startswith("spa"):
        return "es"
    if h.startswith("pt"):
        return "pt"
    t = f" {(text or '').lower()} "
    if any(w in t for w in (" the ", " and ", " your ", " with ", " this ")):
        return "en"
    if any(w in t for w in (" que ", " para ", " con ", " una ", " los ")):
        return "es"
    return "pt"


def _ffmpeg_to_wav(src: str, wav: str, sr: int) -> bool:
    if not shutil.which("ffmpeg"):
        return False
    try:
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                src,
                "-ac",
                "1",
                "-ar",
                str(int(sr)),
                "-sample_fmt",
                "s16",
                wav,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return r.returncode == 0 and os.path.isfile(wav) and os.path.getsize(wav) > 200
    except Exception:
        return False


def _load_audio_any(path: str, sr: int) -> np.ndarray:
    """Lê áudio; se MP3/etc falhar, força decode via ffmpeg → WAV."""
    # 1) soundfile (wav/flac/ogg)
    try:
        import soundfile as sf

        y, file_sr = sf.read(path, always_2d=False)
        y = np.asarray(y, dtype=np.float32)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        if int(file_sr) != int(sr):
            y = _resample(y, int(file_sr), sr)
        if len(y) > 100:
            return y.astype(np.float32)
    except Exception:
        pass

    # 2) ffmpeg → wav temp
    tmp_wav = path + ".__gw.wav"
    try:
        if _ffmpeg_to_wav(path, tmp_wav, sr):
            import soundfile as sf

            y, file_sr = sf.read(tmp_wav, always_2d=False)
            y = np.asarray(y, dtype=np.float32)
            if y.ndim > 1:
                y = np.mean(y, axis=1)
            if int(file_sr) != int(sr):
                y = _resample(y, int(file_sr), sr)
            return y.astype(np.float32)
    except Exception as e:
        last = str(e)
    finally:
        try:
            if os.path.isfile(tmp_wav):
                os.unlink(tmp_wav)
        except OSError:
            pass

    # 3) librosa
    try:
        import librosa

        y, _ = librosa.load(path, sr=sr, mono=True)
        return np.asarray(y, dtype=np.float32)
    except Exception as e:
        raise RuntimeError(f"falha ao ler áudio TTS: {e}") from e


def _resample(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return y.astype(np.float32)
    try:
        import librosa

        return librosa.resample(y.astype(np.float32), orig_sr=sr_in, target_sr=sr_out)
    except Exception:
        n = max(1, int(len(y) * sr_out / max(1, sr_in)))
        x_old = np.linspace(0.0, 1.0, num=len(y), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n, endpoint=False)
        return np.interp(x_new, x_old, y.astype(np.float64)).astype(np.float32)


def _normalize(y: np.ndarray, peak: float = 0.9) -> np.ndarray:
    y = np.asarray(y, dtype=np.float32).flatten()
    p = float(np.max(np.abs(y)) + 1e-12)
    return (y / p * peak).astype(np.float32)


def _fit_duration(y: np.ndarray, sr: int, duracao_s: Optional[float]) -> np.ndarray:
    """Repete a fala com silêncio curto até cobrir a duração da black."""
    if not duracao_s or duracao_s <= 0:
        return y
    n = max(1, int(float(duracao_s) * sr))
    if len(y) >= n:
        return y[:n]
    gap = np.zeros(int(0.18 * sr), dtype=np.float32)
    parts = [y]
    cur = len(y)
    while cur < n:
        parts.append(gap)
        parts.append(y)
        cur += len(gap) + len(y)
    return np.concatenate(parts)[:n].astype(np.float32)


def _run_in_thread(fn, timeout: float = 180.0):
    """Roda bloqueante em thread (evita conflito de event loop do uvicorn)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn)
        return fut.result(timeout=timeout)


def _tts_edge(text: str, sr: int, lang: str) -> Tuple[Optional[np.ndarray], str]:
    try:
        import asyncio
        import edge_tts
    except Exception as e:
        return None, f"edge-tts indisponível: {e}"

    voices = {
        "pt": "pt-BR-FranciscaNeural",
        "en": "en-US-JennyNeural",
        "es": "es-ES-ElviraNeural",
    }
    voice = voices.get(lang, voices["pt"])
    tmp = tempfile.mkdtemp(prefix="gw_edge_")
    out_mp3 = os.path.join(tmp, "speech.mp3")

    def _worker() -> Tuple[Optional[np.ndarray], str]:
        async def _run() -> None:
            comm = edge_tts.Communicate(text, voice)
            await comm.save(out_mp3)

        # Sempre asyncio.run em thread limpa — seguro sob uvicorn
        asyncio.run(_run())
        if not os.path.isfile(out_mp3) or os.path.getsize(out_mp3) < 100:
            return None, "edge-tts não gerou arquivo"
        y = _load_audio_any(out_mp3, sr)
        return _normalize(y), f"edge-tts:{voice}"

    try:
        return _run_in_thread(_worker, timeout=180.0)
    except Exception as e:
        return None, f"edge-tts falhou: {e}"
    finally:
        try:
            if os.path.isfile(out_mp3):
                os.unlink(out_mp3)
            os.rmdir(tmp)
        except Exception:
            pass


def _tts_gtts(text: str, sr: int, lang: str) -> Tuple[Optional[np.ndarray], str]:
    """Google TTS (rede). Decode preferencial via ffmpeg."""
    try:
        from gtts import gTTS
    except Exception as e:
        return None, f"gTTS indisponível: {e}"
    lang_map = {"pt": "pt", "en": "en", "es": "es"}
    gl = lang_map.get(lang, "pt")
    tmp = tempfile.mkdtemp(prefix="gw_gtts_")
    mp3 = os.path.join(tmp, "speech.mp3")
    try:
        gTTS(text=text, lang=gl, slow=False).save(mp3)
        if not os.path.isfile(mp3) or os.path.getsize(mp3) < 100:
            return None, "gTTS não gerou arquivo"
        y = _load_audio_any(mp3, sr)
        return _normalize(y), f"gtts:{gl}"
    except Exception as e:
        return None, f"gTTS falhou: {e}"
    finally:
        try:
            if os.path.isfile(mp3):
                os.unlink(mp3)
            os.rmdir(tmp)
        except Exception:
            pass


def _tts_espeak(text: str, sr: int, lang: str) -> Tuple[Optional[np.ndarray], str]:
    """Offline — ideal na VPS se edge/gTTS falharem."""
    bin_name = shutil.which("espeak-ng") or shutil.which("espeak")
    if not bin_name:
        return None, "espeak não encontrado"
    lang_map = {"pt": "pt-br", "en": "en", "es": "es"}
    voice = lang_map.get(lang, "pt-br")
    tmp = tempfile.mkdtemp(prefix="gw_espeak_")
    wav = os.path.join(tmp, "speech.wav")
    try:
        r = subprocess.run(
            [
                bin_name,
                "-v",
                voice,
                "-s",
                "145",
                "-w",
                wav,
                text,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0 or not os.path.isfile(wav):
            return None, f"espeak falhou: {(r.stderr or r.stdout or '')[:200]}"
        y = _load_audio_any(wav, sr)
        return _normalize(y), f"espeak:{voice}"
    except Exception as e:
        return None, f"espeak falhou: {e}"
    finally:
        try:
            if os.path.isfile(wav):
                os.unlink(wav)
            os.rmdir(tmp)
        except Exception:
            pass


def _tts_macos_say(text: str, sr: int, lang: str) -> Tuple[Optional[np.ndarray], str]:
    if not shutil.which("say"):
        return None, "say não encontrado"
    voices = {
        "pt": ["Luciana", "Joana", "Felipe"],
        "en": ["Samantha", "Alex", "Victoria"],
        "es": ["Monica", "Paulina", "Jorge"],
    }
    voice_list = voices.get(lang, voices["pt"])
    tmp = tempfile.mkdtemp(prefix="gw_say_")
    aiff = os.path.join(tmp, "speech.aiff")
    wav = os.path.join(tmp, "speech.wav")
    last_err = ""
    try:
        for voice in voice_list:
            try:
                r = subprocess.run(
                    ["say", "-v", voice, "-o", aiff, text],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if r.returncode != 0 or not os.path.isfile(aiff):
                    last_err = (r.stderr or r.stdout or "say fail")[:200]
                    continue
                path = aiff
                if shutil.which("ffmpeg") and _ffmpeg_to_wav(aiff, wav, sr):
                    path = wav
                y = _load_audio_any(path, sr)
                return _normalize(y), f"macos-say:{voice}"
            except Exception as e:
                last_err = str(e)
                continue
        return None, f"say falhou: {last_err}"
    finally:
        for p in (aiff, wav):
            try:
                if os.path.isfile(p):
                    os.unlink(p)
            except Exception:
                pass
        try:
            os.rmdir(tmp)
        except Exception:
            pass


def _tts_formant_fallback(
    texto: str, sr: int, duracao_s: Optional[float], f0: float = 160.0
) -> np.ndarray:
    """Último recurso — soa artificial. Evitar em produção."""
    from core.cloaker import bandpass

    chars = [c for c in (texto or "").lower() if c.isalnum() or c == " "]
    if not chars:
        chars = list("oferta especial confira as condicoes oficiais no site")
    n_target = int((duracao_s or max(2.5, len(chars) * 0.075)) * sr)
    vogais = {
        "a": (800, 1200, 2500),
        "e": (500, 1700, 2500),
        "i": (300, 2200, 3000),
        "o": (500, 900, 2400),
        "u": (350, 700, 2300),
    }
    rng = np.random.default_rng(abs(hash(texto)) % (2**31))
    chunks = [np.zeros(int(0.04 * sr))]
    for ch in chars:
        n = max(1, int(0.08 * sr))
        if ch == " ":
            chunks.append(np.zeros(int(0.06 * sr)))
            continue
        forms = vogais.get(ch, (600, 1400, 2400))
        t = np.arange(n) / sr
        pitch = f0 * (1.0 + 0.04 * np.sin(2 * np.pi * 2.2 * t))
        phase = 2 * np.pi * np.cumsum(pitch) / sr
        source = 0.35 * np.sin(phase) + 0.02 * rng.standard_normal(n)
        env = np.ones(n)
        a, r = max(1, n // 10), max(1, n // 5)
        env[:a] = np.linspace(0, 1, a)
        env[-r:] = np.linspace(1, 0, r)
        sig = np.zeros(n)
        for i, f in enumerate(forms):
            sig += (1.0 / (i + 1)) * np.sin(2 * np.pi * f * t)
        sig = (0.85 * sig + 0.15 * source) * env
        chunks.append(sig)
    y = np.concatenate(chunks).astype(np.float64)
    if len(y) < n_target:
        y = np.tile(y, int(np.ceil(n_target / max(1, len(y)))))[:n_target]
    else:
        y = y[:n_target]
    y = bandpass(y, sr, 300.0, 3600.0)
    return _normalize(y.astype(np.float32))


def gerar_fala_white(
    texto: str,
    sr: int,
    duracao_s: Optional[float] = None,
    language: str = "",
) -> Tuple[np.ndarray, dict]:
    """
    Gera áudio de fala da copy white (preferencialmente TTS real).

    Returns:
        (audio mono float32, meta)
    """
    text = " ".join((texto or "").split())
    if not text:
        text = (
            "Oferta especial. Confira as condicoes oficiais no site. "
            "Produto com garantia e suporte ao cliente."
        )
    # edge-tts / gTTS limitam textos muito longos
    if len(text) > 900:
        text = text[:900].rsplit(" ", 1)[0] + "."

    lang = _detect_lang(text, language)
    errors = []

    # Ordem: rede neural → gTTS → offline espeak → macOS → formant
    for fn in (_tts_edge, _tts_gtts, _tts_espeak, _tts_macos_say):
        try:
            y, detail = fn(text, sr, lang)
        except Exception as e:
            errors.append(f"{fn.__name__}: {e}")
            continue
        if y is not None and len(y) > int(sr * 0.25):
            y = _fit_duration(y, sr, duracao_s)
            try:
                from core.cloaker import bandpass

                # banda de voz ampla — mantém inteligibilidade da copy
                y = bandpass(y.astype(np.float64), sr, 80.0, 7500.0).astype(np.float32)
                y = _normalize(y)
            except Exception:
                y = _normalize(y)
            return y, {
                "tts": True,
                "engine": detail,
                "language": lang,
                "chars": len(text),
                "duration_s": round(len(y) / float(sr), 3),
                "is_speech": True,
            }
        errors.append(detail)

    # fallback formant (NÃO é o modelo de mercado)
    y = _tts_formant_fallback(text, sr, duracao_s)
    return y, {
        "tts": False,
        "engine": "formant_fallback",
        "language": lang,
        "errors": errors,
        "is_speech": False,
        "warning": (
            "Nenhum TTS real disponível — soa como barulho. "
            "Na VPS instale: pip install edge-tts gTTS && apt-get install -y espeak-ng ffmpeg"
        ),
        "duration_s": round(len(y) / float(sr), 3),
    }
