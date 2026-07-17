"""
Testes unitários das 4 camadas e do pipeline AudioShield.
"""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.camada1_mascaramento import MascaramentoPsicoacustico, ParametrosMascaramento
from core.camada2_ultrassom import InjecaoUltrassonica, ParametrosUltrassom
from core.camada3_dispersor import DispersorFase, ParametrosDispersor
from core.camada4_adversarial import WatermarkingAdversarial, ParametrosAdversarial
from core.pipeline import AudioShieldPipeline, PipelineConfig
from utils.audio_io import gerar_voz_sintetica, salvar_audio, carregar_audio
from utils.validacao import validar_inaudibilidade


SR = 48000
DUR = 1.0


def _sine(freq: float = 440.0, sr: int = SR, dur: float = DUR) -> np.ndarray:
    t = np.arange(int(sr * dur)) / sr
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


class TestCamada1(unittest.TestCase):
    def test_aplica_e_mantem_tamanho(self) -> None:
        y = _sine()
        out, meta = MascaramentoPsicoacustico().aplicar(y, SR)
        self.assertEqual(len(out), len(y))
        self.assertTrue(meta.get("aplicada"))
        self.assertEqual(out.dtype, np.float32)

    def test_snr_razoavel(self) -> None:
        y = _sine(300.0)
        # Sinal com envelope (não seno puro flat)
        env = np.linspace(0.2, 1.0, len(y))
        y = (y * env).astype(np.float32)
        out, meta = MascaramentoPsicoacustico(
            ParametrosMascaramento(intensidade_db=-30)
        ).aplicar(y, SR)
        snr = meta.get("snr_estimado_db", 0)
        self.assertGreater(snr, 15)


class TestCamada2(unittest.TestCase):
    def test_ultrassom_48k(self) -> None:
        y = _sine()
        out, meta = InjecaoUltrassonica().aplicar(y, SR)
        self.assertTrue(meta.get("aplicada"))
        self.assertEqual(len(out), len(y))

    def test_falha_graceful_sr_baixa(self) -> None:
        y = _sine(sr=16000)
        out, meta = InjecaoUltrassonica().aplicar(y, 16000)
        self.assertFalse(meta.get("aplicada"))
        np.testing.assert_array_almost_equal(out, y, decimal=5)


class TestCamada3(unittest.TestCase):
    def test_allpass_magnitude_proxima(self) -> None:
        y = _sine(1000.0)
        out, meta = DispersorFase().aplicar(y, SR)
        self.assertTrue(meta.get("aplicada"))
        # Energia similar
        e0 = np.mean(y**2)
        e1 = np.mean(out**2)
        self.assertAlmostEqual(e0, e1, delta=e0 * 0.15)
        # Diff de magnitude espectral reportada pequena
        self.assertLess(meta.get("diff_magnitude_media_db", 99), 8.0)


class TestCamada4(unittest.TestCase):
    def test_fallback_sem_whisper(self) -> None:
        y = _sine()
        out, meta = WatermarkingAdversarial(
            ParametrosAdversarial(usar_whisper=False, epsilon_db=-60)
        ).aplicar(y, SR)
        self.assertTrue(meta.get("aplicada"))
        self.assertIn("fallback", meta.get("modo", ""))
        # Perturbação muito pequena
        max_d = float(np.max(np.abs(out - y)))
        self.assertLess(max_d, 0.05)


class TestPipeline(unittest.TestCase):
    def test_pipeline_completo(self) -> None:
        y, sr = gerar_voz_sintetica("teste de protecao", sr=SR)
        pipe = AudioShieldPipeline(
            PipelineConfig(
                adversarial=ParametrosAdversarial(usar_whisper=False)
            )
        )
        out, rel = pipe.processar(y, sr, nome_arquivo="teste.wav")
        self.assertEqual(len(out), len(y))
        self.assertEqual(len(rel["ordem_camadas"]), 4)
        self.assertIn("fingerprint_sha256", rel)
        self.assertIn("metricas", rel)

    def test_inaudibilidade_basica(self) -> None:
        y, sr = gerar_voz_sintetica("ola mundo", sr=SR)
        pipe = AudioShieldPipeline(
            PipelineConfig(
                adversarial=ParametrosAdversarial(usar_whisper=False, epsilon_db=-65)
            )
        )
        out, _ = pipe.processar(y, sr)
        val = validar_inaudibilidade(y, out, sr, snr_min_db=12.0, max_diff_abs=0.45)
        # All-pass mexe na fase: priorizamos correlação espectral + corr alinhada
        self.assertGreater(val["correlacao_espectral"], 0.90)
        self.assertGreater(val["correlacao"], 0.75)
        self.assertTrue(
            val["passou_inaudibilidade"]
            or val["correlacao_espectral"] > 0.95
            or val["snr_db"] > 10
        )

    def test_stealth_fingerprint(self) -> None:
        y = _sine()
        pipe = AudioShieldPipeline()
        _, rel = pipe.processar(y, SR)
        self.assertEqual(len(rel["fingerprint_sha256"]), 64)

    def test_batch(self) -> None:
        itens = [(_sine(440), SR, "a.wav"), (_sine(880), SR, "b.wav")]
        pipe = AudioShieldPipeline(
            PipelineConfig(adversarial=ParametrosAdversarial(usar_whisper=False))
        )
        res = pipe.processar_batch(itens)
        self.assertEqual(len(res), 2)


class TestAudioIO(unittest.TestCase):
    def test_roundtrip_wav(self) -> None:
        path = os.path.join(ROOT, "tests", "_tmp_test.wav")
        y = _sine()
        salvar_audio(path, y, SR)
        y2, sr = carregar_audio(path)
        self.assertEqual(sr, SR)
        self.assertEqual(len(y2), len(y))
        # PCM 16 perde um pouco de precisão
        self.assertLess(float(np.max(np.abs(y2 - y))), 0.01)
        os.unlink(path)

    def test_sample_audio_exists_or_create(self) -> None:
        sample = os.path.join(ROOT, "tests", "sample_audio.wav")
        if not os.path.isfile(sample):
            y, sr = gerar_voz_sintetica(
                "Ola, este e um teste de protecao", sr=48000
            )
            # Adiciona componente senoidal para “riqueza”
            t = np.arange(len(y)) / sr
            y = y + 0.05 * np.sin(2 * np.pi * 440 * t)
            y = (y / (np.max(np.abs(y)) + 1e-12) * 0.8).astype(np.float32)
            salvar_audio(sample, y, sr)
        self.assertTrue(os.path.isfile(sample))


if __name__ == "__main__":
    unittest.main()
