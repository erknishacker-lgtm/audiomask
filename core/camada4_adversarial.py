"""
Camada 4 — Watermarking Adversarial (contra ASR / Whisper).

Tenta forçar erro de transcrição com perturbação mínima (< -60 dB).
Se GPU/torch/whisper não estiverem disponíveis, usa ruído
pseudo-aleatório com espectro focado em formantes (fallback).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np


@dataclass
class ParametrosAdversarial:
    """Parâmetros ajustáveis da Camada 4."""

    epsilon_db: float = -62.0  # intensidade máxima da perturbação
    n_steps: int = 8  # passos de ataque (quando gradiente disponível)
    step_size: float = 0.0005
    alvo_texto: str = ""  # vazio = maximizar perda (untargeted)
    usar_whisper: bool = True
    modelo_whisper: str = "tiny"
    seed: Optional[int] = 99
    bandas_formantes_hz: Tuple[float, float] = (300.0, 3400.0)


class WatermarkingAdversarial:
    """
    Gera perturbação adversarial mínima contra modelos de fala.

    Analogia: como colocar um adesivo minúsculo num código de barras —
    o olho humano (ouvido) não vê, o leitor automático falha.
    """

    def __init__(self, params: Optional[ParametrosAdversarial] = None) -> None:
        self.params = params or ParametrosAdversarial()
        self._modelo = None
        self._processor = None
        self._torch = None
        self._device = "cpu"
        self._whisper_backend: Optional[str] = None  # "transformers" | "openai"

    def aplicar(
        self,
        audio: np.ndarray,
        sr: int,
        params: Optional[ParametrosAdversarial] = None,
    ) -> Tuple[np.ndarray, dict]:
        """
        Aplica watermarking adversarial.

        Returns:
            Áudio perturbado e metadados (inclui modo: gradiente|fallback).
        """
        p = params or self.params
        try:
            y = self._garantir_mono(audio).astype(np.float32)
            if len(y) == 0:
                return y, {"aplicada": False, "aviso": "áudio vazio", "camada": 4}

            eps = 10.0 ** (p.epsilon_db / 20.0)
            modo = "fallback"
            delta = None
            detalhe: dict[str, Any] = {}

            if p.usar_whisper:
                delta, detalhe = self._ataque_gradiente(y, sr, p, eps)
                if delta is not None:
                    modo = detalhe.get("backend", "gradiente")

            if delta is None:
                delta = self._ruido_formantes(y, sr, p, eps)
                modo = "fallback_pseudoaleatorio"
                detalhe = {
                    "motivo": "Whisper/torch indisponível ou falhou",
                    "distribuicao": "formantes_gaussiano_bandpass",
                }

            # Garante ||delta||_inf limitado e energia < eps relativo
            delta = np.clip(delta, -eps, eps)
            # Também limita por RMS relativo
            rms_y = float(np.sqrt(np.mean(y.astype(np.float64) ** 2)) + 1e-12)
            rms_d = float(np.sqrt(np.mean(delta.astype(np.float64) ** 2)) + 1e-12)
            alvo_rms = rms_y * eps
            if rms_d > alvo_rms:
                delta = delta * (alvo_rms / (rms_d + 1e-12))

            out = y + delta.astype(np.float32)
            out = np.clip(out, -1.0, 1.0)

            meta = {
                "aplicada": True,
                "camada": 4,
                "nome": "watermarking_adversarial",
                "modo": modo,
                "epsilon_db": p.epsilon_db,
                "snr_perturbacao_db": self._snr_db(y, delta),
                "rms_delta": float(np.sqrt(np.mean(delta**2))),
                "detalhe": detalhe,
            }
            return out.astype(np.float32), meta

        except Exception as exc:
            return np.asarray(audio, dtype=np.float32), {
                "aplicada": False,
                "erro": str(exc),
                "camada": 4,
            }

    def _ataque_gradiente(
        self,
        y: np.ndarray,
        sr: int,
        p: ParametrosAdversarial,
        eps: float,
    ) -> Tuple[Optional[np.ndarray], dict]:
        """
        Tenta ataque com gradientes via transformers Whisper ou openai-whisper.
        Retorna (None, info) se impossível.
        """
        info: dict[str, Any] = {}
        try:
            import torch

            self._torch = torch
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            info["device"] = self._device
        except Exception as e:
            return None, {"erro_torch": str(e)}

        # Preferência: transformers (melhor para gradientes)
        try:
            return self._ataque_transformers(y, sr, p, eps, info)
        except Exception as e:
            info["erro_transformers"] = str(e)

        # Fallback openai-whisper (gradientes limitados / ruído guiado)
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
        """PGD simplificado sobre encoder Whisper (transformers)."""
        import torch
        from transformers import WhisperProcessor, WhisperForConditionalGeneration

        model_id = f"openai/whisper-{p.modelo_whisper}"
        if self._modelo is None or self._whisper_backend != "transformers":
            self._processor = WhisperProcessor.from_pretrained(model_id)
            self._modelo = WhisperForConditionalGeneration.from_pretrained(model_id)
            self._modelo.to(self._device)
            self._modelo.eval()
            self._whisper_backend = "transformers"

        processor = self._processor
        model = self._modelo

        # Whisper espera 16 kHz
        y16 = self._resample(y, sr, 16000)
        # Limita duração para memória (máx ~30s do Whisper)
        max_samples = 16000 * 30
        y16 = y16[:max_samples]

        inputs = processor(
            y16, sampling_rate=16000, return_tensors="pt"
        )
        input_features = inputs.input_features.to(self._device)
        input_features = input_features.clone().detach().requires_grad_(True)

        # Labels: se sem alvo, usa tokens de pad / decoder start para maximizar loss
        # Untargeted: maximizar loss em relação à predição greedy atual
        with torch.no_grad():
            generated = model.generate(input_features, max_new_tokens=64)
            labels = generated.clone()

        if p.alvo_texto:
            lab = processor.tokenizer(
                p.alvo_texto, return_tensors="pt"
            ).input_ids.to(self._device)
            labels = lab

        delta_feat = torch.zeros_like(input_features, requires_grad=True)
        step = p.step_size

        for i in range(max(1, p.n_steps)):
            adv = input_features + delta_feat
            outputs = model(input_features=adv, labels=labels)
            loss = outputs.loss
            # Untargeted: maximizar loss
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
                # Projeta no limiar de features (aprox. eps * escala)
                delta_feat = torch.clamp(delta_feat, -eps * 10, eps * 10)
                delta_feat = delta_feat.detach().requires_grad_(True)
            info["loss_final"] = float(loss.detach().cpu().item())
            info["steps"] = i + 1

        # Mapeia perturbação de features de volta para o domínio do tempo
        # Aproximação: usa ruído correlacionado com o gradiente projetado no tempo
        with torch.no_grad():
            # Diferença nas features → sinal no tempo via ruído filtrado escalado
            # (inversão exata do mel-spectrograma Whisper é complexa)
            feat_delta = delta_feat.detach().cpu().numpy().squeeze()
            # Energia média por frame → envelope temporal
            frame_energy = np.mean(np.abs(feat_delta), axis=0)
            frame_energy = frame_energy / (np.max(frame_energy) + 1e-12)
            # Interpola envelope para comprimento do áudio 16k
            env = np.interp(
                np.linspace(0, 1, len(y16)),
                np.linspace(0, 1, len(frame_energy)),
                frame_energy,
            )
            rng = np.random.default_rng(p.seed)
            noise = rng.standard_normal(len(y16)).astype(np.float32)
            noise = self._bandpass(noise, 16000, *p.bandas_formantes_hz)
            delta16 = noise * env * eps
            # Escala para respeitar eps
            peak = np.max(np.abs(delta16)) + 1e-12
            delta16 = delta16 * (eps / peak)

        # Volta para sr original
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
        """
        Fallback: openai-whisper não expõe gradientes fáceis —
        gera ruído guiado por score de confiança (busca aleatória).
        """
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
            # Heurística: texto mais curto / mais tokens estranhos = melhor ataque
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

    def _ruido_formantes(
        self,
        y: np.ndarray,
        sr: int,
        p: ParametrosAdversarial,
        eps: float,
    ) -> np.ndarray:
        """
        Fallback: ruído gaussiano filtrado na banda da voz,
        com envelope do sinal e fase pseudo-aleatória (seed fixa).
        """
        rng = np.random.default_rng(p.seed)
        n = len(y)
        noise = rng.standard_normal(n).astype(np.float64)
        noise = self._bandpass(noise, sr, *p.bandas_formantes_hz)

        # Envelope da voz (mascaramento natural)
        env = np.abs(y.astype(np.float64))
        win = max(1, sr // 100)
        kernel = np.ones(win) / win
        env = np.convolve(env, kernel, mode="same")
        env = env / (np.max(env) + 1e-12)

        delta = noise * env
        peak = np.max(np.abs(delta)) + 1e-12
        delta = delta * (eps / peak)
        return delta.astype(np.float32)

    @staticmethod
    def _bandpass(
        x: np.ndarray, sr: int, f_lo: float, f_hi: float
    ) -> np.ndarray:
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
            return y.astype(np.float32)
        try:
            import librosa

            return librosa.resample(
                y.astype(np.float32), orig_sr=sr_in, target_sr=sr_out
            )
        except Exception:
            # Linear interpolation fallback
            n_out = int(len(y) * sr_out / sr_in)
            xp = np.linspace(0, 1, len(y))
            xq = np.linspace(0, 1, max(1, n_out))
            return np.interp(xq, xp, y).astype(np.float32)

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
        """
        Transcreve áudio com Whisper se disponível (para demo de ataque).
        """
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
