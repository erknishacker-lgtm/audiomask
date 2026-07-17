# MASK.SOUND — Proteção Invisível de Áudio

Marca: **MASK.SOUND** · logo em `assets/logo.png` · tema carvão + ciano (fundo escuro para o logo não sumir).

## Conta admin (padrão)

| Campo | Valor |
|--------|--------|
| E-mail | `admin@audiomask.com` |
| Senha | `Admin@AudioMask2026` |

**Troque a senha em produção** (painel admin → editar usuário).

### Planos
- **Free:** 2 vídeos grátis  
- **Pro:** R$ 49,90 · cota prática ilimitada (admin ativa)

### App web (principal)
Frontend premium em `web/` + API FastAPI em `api/`.

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8501
# abra http://localhost:8501
```

- Login / cadastro · PT / EN  
- Dashboard moderno · proteger mídia · conta · admin  
- CapCut / TikTok / redes com preset anti-legenda  

Streamlit legado: `streamlit run app.py` (opcional).

---

# AudioShield — Proteção Invisível Avançada

Sistema completo de **proteção de áudio em 4 camadas**, com interface Streamlit, dashboard espectral, export WAV/MP3, **vídeo MP4** e modo adversarial (Whisper).

> **Analogia:** é como um vidro blindado transparente no som — o ouvido humano quase não nota diferença, mas leitores automáticos (ASR) e cópias maliciosas sofrem interferência.
>
> No **vídeo**, o app só troca a trilha sonora: a imagem fica igual; o áudio sai protegido.

---

## O que cada camada faz

| Camada | Nome | Ideia em linguagem simples |
|--------|------|----------------------------|
| 1 | Mascaramento psicoacústico | Esconde tons na região da voz (2.5–3.5 kHz) usando o volume da própria fala |
| 2 | Injeção ultrassônica | Coloca ruído em ~19.5 kHz, quase inaudível, captado por microfones |
| 3 | Dispersor de fase (all-pass) | Muda o “timing” interno das frequências sem mudar o volume de cada uma |
| 4 | Watermark adversarial | Perturbação mínima para confundir Whisper/ASR (com fallback sem GPU) |

### Detalhe técnico

#### Camada 1 — Mascaramento psicoacústico
- Extrai o **envelope** da voz (Hilbert).
- Injeta tons puros entre 2.5–3.5 kHz modulados por esse envelope.
- Refina a **fase** via STFT/FFT para maximizar o mascaramento.

#### Camada 2 — Ultrassom
- Gera ruído branco → **filtro passa-alta** (~18 kHz).
- Modula com portadora em **19.5 kHz**.
- Mixa entre **-40 dB e -50 dB** (imperceptível para a maioria dos adultos).
- Requer sample rate ≥ 44.1 kHz (recomendado 48 kHz).

#### Camada 3 — All-pass IIR 4ª ordem
- Cascata de 4 seções all-pass de 1ª ordem.
- **Magnitude ≈ constante**; só a fase / group delay (2–15 ms) muda.
- Efeito espectral de potência quase invisível no dashboard.

#### Camada 4 — Adversarial
- Com torch + transformers: PGD simplificado sobre Whisper-tiny.
- Sem GPU/modelo: ruído gaussiano em banda de formantes, &lt; -60 dB.
- Nunca derruba o pipeline se o Whisper falhar.

---

## Estrutura

```
AudioShield/
├── app.py                 # Interface Streamlit
├── demo.py                # Demonstração CLI
├── core/
│   ├── camada1_mascaramento.py
│   ├── camada2_ultrassom.py
│   ├── camada3_dispersor.py
│   ├── camada4_adversarial.py
│   └── pipeline.py
├── utils/
│   ├── audio_io.py
│   ├── espectro.py
│   └── validacao.py
├── tests/
│   ├── test_camadas.py
│   ├── gerar_sample.py
│   └── sample_audio.wav
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Instalação rápida (local)

```bash
cd AudioShield

# Ambiente virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Dependências
pip install -U pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# ffmpeg (obrigatório para MP3 e MP4) — macOS:
brew install ffmpeg
# Ubuntu:
# sudo apt-get install ffmpeg libsndfile1

# Áudio de exemplo
python tests/gerar_sample.py

# Interface
streamlit run app.py
```

Abra `http://localhost:8501`.

### Vídeo MP4 na interface

1. Fonte → **Upload vídeo (MP4/MOV)**  
2. Envie o arquivo  
3. **Aplicar proteção**  
4. Baixe **MP4 protegido** (imagem original + áudio com as 4 camadas)

Na CLI:

```bash
python demo.py --demo-video
python demo.py --video /caminho/meu_video.mp4
```

API:

```python
from core.pipeline import AudioShieldPipeline
from utils.video_io import proteger_video

pipe = AudioShieldPipeline()
proteger_video("entrada.mp4", pipe, "saida_protegida.mp4")
```

### Demo CLI

```bash
python demo.py
python demo.py --whisper          # tenta Whisper (mais lento)
python demo.py --sr 48000 --texto "Ola mundo"
python demo.py --demo-video       # gera e protege um MP4 de teste
```

### Testes

```bash
python -m unittest tests.test_camadas tests.test_video -v
```

---

## Docker

```bash
cd AudioShield
docker compose up --build
```

Interface em `http://localhost:8501`.

Volumes:
- `./output` → áudios protegidos  
- `./reports` → JSON de parâmetros/métricas  

Só a imagem:

```bash
docker build -t audioshield .
docker run --rm -p 8501:8501 -v "$(pwd)/output:/app/output" audioshield
```

---

## Uso da interface

1. **Upload** WAV/MP3, ou gere **voz sintética**, ou use o **sample**.
2. Ajuste camadas e intensidades na barra lateral.
3. Clique **Aplicar proteção**.
4. **Compare** original vs protegido (players lado a lado).
5. Veja o **dashboard** (espectrograma antes/depois + diferença).
6. Baixe **WAV**, **MP3** (bitrate variável) e **relatório JSON**.
7. (Opcional) Transcreva com Whisper para ver impacto no ASR.
8. **Batch**: envie vários arquivos no expander.

### Relatório JSON

Cada processamento grava parâmetros, ordem das camadas, SNR, fingerprint SHA-256 e tag stealth em `reports/`.

### Modo Stealth

Detecta indício de ultrassom prévio (energia &gt; 18 kHz) e avisa antes de reprocessar.

---

## API Python mínima

```python
from core.pipeline import AudioShieldPipeline, PipelineConfig
from utils.audio_io import carregar_audio, salvar_audio

y, sr = carregar_audio("meu_audio.wav", sr_alvo=48000)
pipe = AudioShieldPipeline(PipelineConfig())
protegido, relatorio = pipe.processar(y, sr, nome_arquivo="meu_audio.wav")
salvar_audio("protegido.wav", protegido, sr)
pipe.salvar_relatorio(relatorio, "relatorio.json")
```

---

## Evidências de sucesso

| Critério | Como verificar |
|----------|----------------|
| (a) Quase inaudível | SNR alto, correlação temporal &gt; 0.95, ouça A/B no app |
| (b) Confunde ASR | Ative Whisper no demo/app e compare transcrições |

> Métricas objetivas **não substituem** teste auditivo humano. Ultrassom depende de idade, equipamento e sample rate.

---

## Limitações honestas

- Compressão agressiva (WhatsApp, alguns MP3 baixos) pode **apagar** o ultrassom.
- O ataque adversarial real contra Whisper é **não-trivial**; o modo gradiente é simplificado e o fallback é heurístico.
- Não é garantia legal de “anti-gravação” nem anti-deepfake forense certificada.
- **Uso ético:** proteja *seus* conteúdos e privacidade. Não use para fraudar autenticação por voz ou violar leis.

---

## Dependências principais

- `streamlit` — UI  
- `numpy` / `scipy` — DSP  
- `librosa` / `soundfile` / `pydub` — I/O e análise  
- `matplotlib` / `plotly` — gráficos  
- `torch` + `transformers` + `openai-whisper` — camada 4 (opcional em runtime)

---

## Licença e responsabilidade

Software educacional/experimental. Você é responsável pelo uso. Os autores não se responsabilizam por usos indevidos.

---

## O que isso significa (resumo)

Você sobe um áudio, o AudioShield aplica quatro “camadas de tinta invisível” no som, mostra o gráfico provando que o espectro quase não mudou na região audível, deixa você ouvir os dois lados e baixar o arquivo protegido + um relatório de tudo que foi feito.
