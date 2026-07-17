"""
Camada 4 — Anti-legenda / anti-ASR (CapCut, Whisper, redes).

Importante:
  Ultrassom e ruído a -60 dB NÃO quebram CapCut (eles filtram e usam ASR na voz).
  Esta camada ataca a FAIXA DA FALA (≈200–4000 Hz): fase, formantes, eco micro e ruído
  com envelope da voz — o que realmente atrapalha legenda automática.

Modos:
  stealth     — menos audível, menos eficaz
  balanced    — equilíbrio
  aggressive  — prioriza quebrar ASR (recomendado para CapCut/TikTok)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np


@dataclass
class ParametrosAdversarial:
    """Parâmetros da camada anti-legenda."""

    # SNR da perturbação vs RMS do sinal (dB). -16 = forte; -35 = fraco
    epsilon_db: float = -18.0
    n_steps: int = 6
    step_size: float = 0.001
    alvo_texto: str = ""
    usar_whisper: bool = False  # DSP anti-ASR é o default confiável
    modelo_whisper: str = "tiny"
    seed: Optional[int] = 99
    bandas_formantes_hz: Tuple[float, float] = (200.0, 4200.0)
    # stealth | balanced | aggressive
    forca: str = "aggressive"
    # misturas internas (0–1)
    peso_fase: float = 0.85
    peso_ruido: float = 0.75
    peso_eco: float = 0.55
    peso_warp: float = 0.45
    peso_pitch: float = 0.35


# Presets de força → epsilon e pesos
_FORCA_PRESETS = {
    "stealth": {
        "epsilon_db": -32.0,
        "peso_fase": 0.45,
        "peso_ruido": 0.35,
        "peso_eco": 0.2,
        "peso_warp": 0.15,
        "peso_pitch": 0.1,
    },
    "balanced": {
        "epsilon_db": -24.0,
        "peso_fase": 0.7,
        "peso_ruido": 0.55,
        "peso_eco": 0.4,
        "peso_warp": 0.3,
        "peso_pitch": 0.25,
    },
    "aggressive": {
        # Forte o bastante p/ atrapalhar CapCut, sem virar ruído puro
        "epsilon_db": -20.0,
        "peso_fase": 0.8,
        "peso_ruido": 0.7,
        "peso_eco": 0.5,
        "peso_warp": 0.4,
        "peso_pitch": 0.35,
    },
}


class WatermarkingAdversarial:
    """
    Ataque multi-estratégia à faixa da voz para confundir ASR/legendas.
    """

    def __init__(self, params: Optional[ParametrosAdversarial] = None) -> None:
        self.params = params or ParametrosAdversarial()
        self._modelo = None
        self._processor = None
        self._torch = None
        self._device = "cpu"
        self._whisper_backend: Optional[str] = None

    def aplicar(
        self,
        audio: np.ndarray,
        sr: int,
        params: Optional[ParametrosAdversarial] = None,
    ) -> Tuple[np.ndarray, dict]:
        p = self._com_preset(params or self.params)
        try:
            y = self._garantir_mono(audio).astype(np.float64)
            if len(y) == 0:
                return y.astype(np.float32), {
                    "aplicada": False,
                    "aviso": "áudio vazio",
                    "camada": 4,
                }

            rng = np.random.default_rng(p.seed)
            y0 = y.copy()

            # 1) Núcleo DSP anti-ASR (sempre)
            y_atk, detalhe = self._ataque_dsp_anti_asr(y, sr, p, rng)

            modo = f"dsp_anti_asr_{p.forca}"

            # 2) Opcional: reforço Whisper se pedido e disponível
            if p.usar_whisper:
                eps = 10.0 ** (p.epsilon_db / 20.0)
                delta_w, det_w = self._ataque_gradiente(
                    y_atk.astype(np.float32), sr, p, eps
                )
                if delta_w is not None:
                    y_atk = np.clip(y_atk + delta_w.astype(np.float64), -1.0, 1.0)
                    modo += "+whisper"
                    detalhe["whisper"] = det_w

            # Normaliza energia próxima do original (evita “estourar”)
            rms0 = float(np.sqrt(np.mean(y0**2)) + 1e-12)
            rms1 = float(np.sqrt(np.mean(y_atk**2)) + 1e-12)
            y_atk = y_atk * (rms0 / rms1)
            y_atk = np.clip(y_atk, -1.0, 1.0)

            delta = y_atk - y0
            meta = {
                "aplicada": True,
                "camada": 4,
                "nome": "anti_legenda_asr",
                "modo": modo,
                "forca": p.forca,
                "epsilon_db": p.epsilon_db,
                "snr_perturbacao_db": self._snr_db(y0, delta),
                "rms_delta": float(np.sqrt(np.mean(delta**2))),
                "detalhe": detalhe,
                "aviso_capcut": (
                    "ASR comercial (CapCut) é robusto; modo aggressive reduz muito "
                    "a taxa de acerto, mas não há garantia de 0% de legenda."
                ),
            }
            return y_atk.astype(np.float32), meta

        except Exception as exc:
            return np.asarray(audio, dtype=np.float32), {
                "aplicada": False,
                "erro": str(exc),
                "camada": 4,
            }

    def _com_preset(self, p: ParametrosAdversarial) -> ParametrosAdversarial:
        """Aplica preset de força se reconhecido."""
        key = (p.forca or "aggressive").lower().strip()
        if key in _FORCA_PRESETS:
            pr = _FORCA_PRESETS[key]
            return ParametrosAdversarial(
                epsilon_db=float(pr["epsilon_db"]),
                n_steps=p.n_steps,
                step_size=p.step_size,
                alvo_texto=p.alvo_texto,
                usar_whisper=p.usar_whisper,
                modelo_whisper=p.modelo_whisper,
                seed=p.seed,
                bandas_formantes_hz=p.bandas_formantes_hz,
                forca=key,
                peso_fase=float(pr["peso_fase"]),
                peso_ruido=float(pr["peso_ruido"]),
                peso_eco=float(pr["peso_eco"]),
                peso_warp=float(pr["peso_warp"]),
                peso_pitch=float(pr["peso_pitch"]),
            )
        return p

    def _ataque_dsp_anti_asr(
        self,
        y: np.ndarray,
        sr: int,
        p: ParametrosAdversarial,
        rng: np.random.Generator,
    ) -> Tuple[np.ndarray, dict]:
        """
        Combina várias distorções na banda da fala.
        """
        det: dict[str, Any] = {"estrategias": []}
        out = y.copy()
        f_lo, f_hi = p.bandas_formantes_hz

        # --- A) Embaralhamento de fase STFT na banda da voz ---
        if p.peso_fase > 0.01:
            out = self._fase_scramble(out, sr, f_lo, f_hi, p.peso_fase, rng)
            det["estrategias"].append("fase_stft")

        # --- B) Ruído formante com envelope da voz (SNR alvo) ---
        if p.peso_ruido > 0.01:
            noise = self._ruido_formantes_snr(out, sr, p, rng)
            out = out + noise * p.peso_ruido
            det["estrategias"].append("ruido_formantes")

        # --- C) Micro-ecos (multipath) — atrapalha alinhamento do ASR ---
        if p.peso_eco > 0.01:
            out = self._micro_ecos(out, sr, p.peso_eco, rng)
            det["estrategias"].append("micro_eco")

        # --- D) Time-warp local (acelera/desacelera pedaços curtos) ---
        if p.peso_warp > 0.01:
            out = self._time_warp(out, sr, p.peso_warp, rng)
            det["estrategias"].append("time_warp")

        # --- E) Pitch jitter leve ---
        if p.peso_pitch > 0.01:
            out = self._pitch_jitter(out, sr, p.peso_pitch, rng)
            det["estrategias"].append("pitch_jitter")

        # --- F) Notches espectrais errantes nos formantes ---
        out = self._notches_formantes(out, sr, f_lo, f_hi, rng)
        det["estrategias"].append("notches")

        # Soft clip
        out = np.tanh(out * 1.15) / np.tanh(1.15)
        det["bandas_hz"] = [f_lo, f_hi]
        return out, det

    def _fase_scramble(
        self,
        y: np.ndarray,
        sr: int,
        f_lo: float,
        f_hi: float,
        intensidade: float,
        rng: np.random.Generator,
        n_fft: int = 1024,
        hop: int = 256,
    ) -> np.ndarray:
        n = len(y)
        if n < n_fft:
            return y
        window = np.hanning(n_fft)
        out = np.zeros(n)
        norm = np.zeros(n)
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
        mask = (freqs >= f_lo) & (freqs <= f_hi)

        for start in range(0, n - n_fft + 1, hop):
            frame = y[start : start + n_fft] * window
            spec = np.fft.rfft(frame)
            mag = np.abs(spec)
            phase = np.angle(spec)
            # Embaralha fase só na banda da fala
            jitter = rng.uniform(-np.pi, np.pi, size=phase.shape) * intensidade
            phase_new = phase.copy()
            phase_new[mask] = phase[mask] + jitter[mask]
            # Em frames fortes, inverte trechos de fase (quebra coerência)
            if rng.random() < 0.25 * intensidade:
                phase_new[mask] = -phase_new[mask]
            recon = np.fft.irfft(mag * np.exp(1j * phase_new), n=n_fft).real
            out[start : start + n_fft] += recon * window
            norm[start : start + n_fft] += window**2

        norm = np.maximum(norm, 1e-8)
        mixed = out / norm
        # Mistura com original conforme intensidade
        alpha = 0.35 + 0.35 * float(np.clip(intensidade, 0, 1))
        return (1 - alpha) * y + alpha * mixed

    def _ruido_formantes_snr(
        self,
        y: np.ndarray,
        sr: int,
        p: ParametrosAdversarial,
        rng: np.random.Generator,
    ) -> np.ndarray:
        n = len(y)
        noise = rng.standard_normal(n)
        noise = self._bandpass(noise, sr, *p.bandas_formantes_hz)
        # Envelope da voz
        env = np.abs(y)
        win = max(1, sr // 80)
        env = np.convolve(env, np.ones(win) / win, mode="same")
        env = env / (np.max(env) + 1e-12)
        # Tomos em formantes típicos (F1/F2/F3) modulados
        t = np.arange(n) / float(sr)
        f1, f2, f3 = 700.0, 1600.0, 2600.0
        tones = (
            0.5 * np.sin(2 * np.pi * f1 * t + rng.uniform(0, 2 * np.pi))
            + 0.35 * np.sin(2 * np.pi * f2 * t + rng.uniform(0, 2 * np.pi))
            + 0.25 * np.sin(2 * np.pi * f3 * t + rng.uniform(0, 2 * np.pi))
        )
        tones = self._bandpass(tones, sr, *p.bandas_formantes_hz)
        shaped = (0.65 * noise + 0.35 * tones) * env

        # Escala para SNR alvo (epsilon_db)
        rms_y = float(np.sqrt(np.mean(y**2)) + 1e-12)
        rms_n = float(np.sqrt(np.mean(shaped**2)) + 1e-12)
        alvo = rms_y * (10.0 ** (p.epsilon_db / 20.0))
        shaped = shaped * (alvo / rms_n)
        return shaped

    def _micro_ecos(
        self,
        y: np.ndarray,
        sr: int,
        intensidade: float,
        rng: np.random.Generator,
    ) -> np.ndarray:
        out = y.copy()
        # 3 ecos curtos (5–40 ms) com polaridade aleatória
        for _ in range(3):
            delay_ms = float(rng.uniform(5.0, 40.0))
            d = int(delay_ms * 1e-3 * sr)
            if d <= 0 or d >= len(y):
                continue
            g = float(rng.uniform(0.08, 0.28)) * intensidade
            if rng.random() < 0.5:
                g = -g
            eco = np.zeros_like(y)
            eco[d:] = y[:-d]
            out = out + g * eco
        return out

    def _time_warp(
        self,
        y: np.ndarray,
        sr: int,
        intensidade: float,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Acelera/desacelera pedaços de ~40–80 ms."""
        n = len(y)
        if n < sr // 5:
            return y
        out = []
        pos = 0
        while pos < n:
            seg_len = int(rng.uniform(0.04, 0.09) * sr)
            seg = y[pos : pos + seg_len]
            if len(seg) < 8:
                out.append(seg)
                break
            # fator 0.92–1.08 escalado pela intensidade
            span = 0.08 * intensidade
            factor = float(rng.uniform(1.0 - span, 1.0 + span))
            new_len = max(4, int(len(seg) / factor))
            x_old = np.linspace(0, 1, len(seg))
            x_new = np.linspace(0, 1, new_len)
            warped = np.interp(x_new, x_old, seg)
            out.append(warped)
            pos += seg_len
        w = np.concatenate(out)
        # Ajusta comprimento
        if len(w) > n:
            w = w[:n]
        elif len(w) < n:
            w = np.pad(w, (0, n - len(w)))
        # Crossfade suave com original
        mix = 0.2 + 0.35 * intensidade
        return (1 - mix) * y + mix * w

    def _pitch_jitter(
        self,
        y: np.ndarray,
        sr: int,
        intensidade: float,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Pitch shift global leve via reamostragem + volta ao tamanho."""
        # ± semitons * intensidade (até ~1 semitom)
        semitones = float(rng.uniform(-1.2, 1.2)) * intensidade
        factor = 2.0 ** (semitones / 12.0)
        n = len(y)
        n2 = max(8, int(n / factor))
        stretched = np.interp(
            np.linspace(0, n - 1, n2),
            np.arange(n),
            y,
        )
        # Volta ao comprimento original (muda pitch mantendo duração aproximada)
        out = np.interp(
            np.linspace(0, len(stretched) - 1, n),
            np.arange(len(stretched)),
            stretched,
        )
        mix = 0.4 * intensidade
        return (1 - mix) * y + mix * out

    def _notches_formantes(
        self,
        y: np.ndarray,
        sr: int,
        f_lo: float,
        f_hi: float,
        rng: np.random.Generator,
        n_fft: int = 2048,
    ) -> np.ndarray:
        """Atenuação estreita em 2–4 frequências de formante."""
        n = len(y)
        if n < n_fft:
            return y
        # Processa em blocos longos
        out = y.copy()
        hop = n_fft
        window = np.hanning(n_fft)
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
        for start in range(0, n - n_fft + 1, hop // 2):
            frame = out[start : start + n_fft] * window
            spec = np.fft.rfft(frame)
            for _ in range(3):
                f0 = float(rng.uniform(max(f_lo, 400), min(f_hi, 3200)))
                width = float(rng.uniform(40, 120))
                notch = np.exp(-0.5 * ((freqs - f0) / width) ** 2)
                atten = 1.0 - 0.55 * notch  # corta até -55% na região
                spec = spec * atten
            recon = np.fft.irfft(spec, n=n_fft).real
            # OLA simples
            out[start : start + n_fft] = (
                0.5 * out[start : start + n_fft] + 0.5 * recon * window
            )
        return out

    def _ataque_gradiente(
        self,
        y: np.ndarray,
        sr: int,
        p: ParametrosAdversarial,
        eps: float,
    ) -> Tuple[Optional[np.ndarray], dict]:
        info: dict[str, Any] = {}
        try:
            import torch

            self._torch = torch
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            info["device"] = self._device
        except Exception as e:
            return None, {"erro_torch": str(e)}

        try:
            return self._ataque_transformers(y, sr, p, eps, info)
        except Exception as e:
            info["erro_transformers"] = str(e)

        try:
            return self._ataque_openai_whisper(y, sr, p, eps, info)
        except Exception as e:
            info["erro_openai_whisper"] = str(e)
            return None, info

    def _ataque_transformers(
        self,
        y: np.ndarray,
        sr: int,
        p: ParametrosAdversarial,
        eps: float,
        info: dict,
    ) -> Tuple[Optional[np.ndarray], dict]:
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        model_id = f"openai/whisper-{p.modelo_whisper}"
        if self._modelo is None or self._whisper_backend != "transformers":
            self._processor = WhisperProcessor.from_pretrained(model_id)
            self._modelo = WhisperForConditionalGeneration.from_pretrained(model_id)
            self._modelo.to(self._device)
            self._modelo.eval()
            self._whisper_backend = "transformers"

        processor = self._processor
        model = self._modelo
        y16 = self._resample(y, sr, 16000)[: 16000 * 30]

        inputs = processor(y16, sampling_rate=16000, return_tensors="pt")
        input_features = inputs.input_features.to(self._device)
        input_features = input_features.clone().detach().requires_grad_(True)

        with torch.no_grad():
            generated = model.generate(input_features, max_new_tokens=64)
            labels = generated.clone()

        if p.alvo_texto:
            lab = processor.tokenizer(p.alvo_texto, return_tensors="pt").input_ids.to(
                self._device
            )
            labels = lab

        delta_feat = torch.zeros_like(input_features, requires_grad=True)
        step = p.step_size
        for i in range(max(1, p.n_steps)):
            adv = input_features + delta_feat
            outputs = model(input_features=adv, labels=labels)
            loss = outputs.loss
            if not p.alvo_texto:
                loss = -loss
            model.zero_grad()
            if delta_feat.grad is not None:
                delta_feat.grad.zero_()
            loss.backward()
            with torch.no_grad():
                grad = delta_feat.grad
                if grad is None:
                    break
                delta_feat = delta_feat + step * grad.sign()
                delta_feat = torch.clamp(delta_feat, -eps * 20, eps * 20)
                delta_feat = delta_feat.detach().requires_grad_(True)
            info["loss_final"] = float(loss.detach().cpu().item())
            info["steps"] = i + 1

        with torch.no_grad():
            feat_delta = delta_feat.detach().cpu().numpy().squeeze()
            frame_energy = np.mean(np.abs(feat_delta), axis=0)
            frame_energy = frame_energy / (np.max(frame_energy) + 1e-12)
            env = np.interp(
                np.linspace(0, 1, len(y16)),
                np.linspace(0, 1, len(frame_energy)),
                frame_energy,
            )
            rng = np.random.default_rng(p.seed)
            noise = rng.standard_normal(len(y16)).astype(np.float32)
            noise = self._bandpass(noise, 16000, *p.bandas_formantes_hz)
            delta16 = noise * env
            peak = np.max(np.abs(delta16)) + 1e-12
            delta16 = delta16 * (eps / peak)

        delta = self._resample(delta16, 16000, sr)
        if len(delta) < len(y):
            delta = np.pad(delta, (0, len(y) - len(delta)))
        else:
            delta = delta[: len(y)]
        info["backend"] = "transformers_pgd"
        info["modelo"] = model_id
        return delta.astype(np.float32), info

    def _ataque_openai_whisper(
        self,
        y: np.ndarray,
        sr: int,
        p: ParametrosAdversarial,
        eps: float,
        info: dict,
    ) -> Tuple[Optional[np.ndarray], dict]:
        import whisper

        model = whisper.load_model(p.modelo_whisper, device=self._device)
        y16 = self._resample(y, sr, 16000).astype(np.float32)
        rng = np.random.default_rng(p.seed)
        best_delta = None
        best_score = -1e9
        for i in range(max(3, p.n_steps)):
            noise = rng.standard_normal(len(y16)).astype(np.float32)
            noise = self._bandpass(noise, 16000, *p.bandas_formantes_hz)
            peak = np.max(np.abs(noise)) + 1e-12
            cand = noise * (eps / peak)
            adv = np.clip(y16 + cand, -1.0, 1.0)
            result = model.transcribe(adv, fp16=False, language="pt")
            text = (result.get("text") or "").strip()
            no_speech = 0.0
            for seg in result.get("segments") or []:
                no_speech = max(no_speech, float(seg.get("no_speech_prob", 0.0)))
            score = no_speech + (1.0 / (1.0 + len(text)))
            if score > best_score:
                best_score = score
                best_delta = cand
            info["ultima_transcricao"] = text[:200]
            info["best_score"] = float(best_score)
        if best_delta is None:
            return None, info
        delta = self._resample(best_delta, 16000, sr)
        if len(delta) < len(y):
            delta = np.pad(delta, (0, len(y) - len(delta)))
        else:
            delta = delta[: len(y)]
        info["backend"] = "openai_whisper_random_search"
        return delta.astype(np.float32), info

    @staticmethod
    def _bandpass(x: np.ndarray, sr: int, f_lo: float, f_hi: float) -> np.ndarray:
        try:
            from scipy.signal import butter, sosfiltfilt

            nyq = sr / 2.0
            lo = max(f_lo / nyq, 0.001)
            hi = min(f_hi / nyq, 0.99)
            if lo >= hi:
                return x
            sos = butter(4, [lo, hi], btype="band", output="sos")
            return sosfiltfilt(sos, x)
        except Exception:
            return x

    @staticmethod
    def _resample(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
        if sr_in == sr_out:
            return np.asarray(y, dtype=np.float32)
        try:
            import librosa

            return librosa.resample(
                np.asarray(y, dtype=np.float32), orig_sr=sr_in, target_sr=sr_out
            )
        except Exception:
            n_out = int(len(y) * sr_out / sr_in)
            return np.interp(
                np.linspace(0, 1, max(1, n_out)),
                np.linspace(0, 1, len(y)),
                y,
            ).astype(np.float32)

    @staticmethod
    def _garantir_mono(audio: np.ndarray) -> np.ndarray:
        a = np.asarray(audio)
        if a.ndim == 1:
            return a
        if a.ndim == 2:
            if a.shape[0] <= 8 and a.shape[0] < a.shape[1]:
                return np.mean(a, axis=0)
            return np.mean(a, axis=1)
        return a.flatten()

    @staticmethod
    def _snr_db(sinal: np.ndarray, ruido: np.ndarray) -> float:
        ps = float(np.mean(np.asarray(sinal, dtype=np.float64) ** 2)) + 1e-12
        pr = float(np.mean(np.asarray(ruido, dtype=np.float64) ** 2)) + 1e-12
        return float(10.0 * np.log10(ps / pr))

    def transcrever(
        self, audio: np.ndarray, sr: int, language: str = "pt"
    ) -> str:
        try:
            y16 = self._resample(
                self._garantir_mono(audio).astype(np.float32), sr, 16000
            )
            try:
                import whisper

                model = whisper.load_model(
                    self.params.modelo_whisper, device=self._device
                )
                r = model.transcribe(y16, fp16=False, language=language)
                return (r.get("text") or "").strip()
            except Exception:
                pass
            try:
                from transformers import pipeline as hf_pipeline

                pipe = hf_pipeline(
                    "automatic-speech-recognition",
                    model=f"openai/whisper-{self.params.modelo_whisper}",
                    device=-1,
                )
                out = pipe({"array": y16, "sampling_rate": 16000})
                return (out.get("text") or str(out)).strip()
            except Exception as e:
                return f"[ASR indisponível: {e}]"
        except Exception as e:
            return f"[erro: {e}]"
