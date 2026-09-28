<div align="center">

# 🎙️ Transcriber

**Aplicação leve, rápida e moderna para transcrição de áudios e vídeos.**  
*Execute 100% offline no seu computador (com faster-whisper ou whisper.cpp) ou acelere na nuvem (Groq, OpenAI, Gemini).*

[![CI Pipeline](https://github.com/realkalashnikov/transcriber/actions/workflows/ci.yml/badge.svg)](https://github.com/realkalashnikov/transcriber/actions)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![faster-whisper](https://img.shields.io/badge/faster--whisper-CTranslate2-orange)
![whisper.cpp](https://img.shields.io/badge/whisper.cpp-GGML-blueviolet)
![License MIT](https://img.shields.io/badge/License-MIT-green.svg)

<br>

![Transcriber Interface](docs/screenshots/transcription_view.png)

</div>

---

## ✨ Destaques

- 🚀 **Zero Complicação (Sem Docker e Sem Node.js)**: Roda com apenas um comando Python no Windows/Linux/macOS.
- 💻 **Modo Local Offline & Privado**:
  - **faster-whisper**: Acelerado com CTranslate2 e quantização `int8` rápida para CPU (ou `float16` via CUDA se GPU disponível).
  - **whisper.cpp**: Execução otimizada em C++ via GGML (`pywhispercpp`).
  - **Decodificação Nativa via PyAV**: Suporta MP3, WAV, M4A, OGG, FLAC, MP4, MKV, WebM, etc. sem depender do `ffmpeg.exe` externo.
- ☁️ **Modo Nuvem Opcional (via API Key)**:
  - **Groq Whisper**: Transcrições ultrarrápidas de áudios longos em segundos.
  - **OpenAI Whisper**: Transcrição oficial Whisper-1.
  - **Google Gemini**: Transcrição de alta fidelidade com Gemini 2.5 Flash.
  - Chaves de API salvas com segurança direto no `localStorage` do seu navegador.
- 🎧 **Player de Áudio Integrado & Minutagem Interativa**:
  - Clique em qualquer timestamp (`00:15 - 00:22`) para pular o áudio diretamente para o trecho.
- 💾 **Histórico Permanente no Disco**:
  - Suas transcrições são salvas automaticamente em disco. Reinicie o servidor ou feche o navegador sem perder nenhum resultado.
- 🔍 **Busca em Tempo Real**:
  - Encontre qualquer palavra ou frase com destaque dinâmico (*highlight*).
- 📤 **Exportação em 1 Clique**:
  - **TXT** (texto corrido)
  - **SRT** (legendas sincronizadas para VLC, YouTube, Premiere)
  - **VTT** (legendas web)
  - **JSON** (metadados estruturados completos)

---

## ⚡ Como Iniciar no Windows

### Opção 1: Dois cliques (Mais fácil)
Basta dar dois cliques no arquivo:
```cmd
run.bat
```

### Opção 2: Pelo Terminal
```powershell
python run.py
```
O servidor iniciará em `http://localhost:8000` e seu navegador padrão será aberto automaticamente!

---

## 📦 Instalação Manual

Se for executar em outra máquina pela primeira vez:

```bash
# 1. Clone o repositório
git clone https://github.com/realkalashnikov/transcriber.git
cd transcriber

# 2. Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\activate   # No Windows
# source .venv/bin/activate  # No Linux/macOS

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie
python run.py
```

---

## 📊 Guia de Modelos Locais (Whisper)

| Modelo | Parâmetros | RAM Recomendada | Velocidade Relativa | Uso Recomendado |
|---|---|---|---|---|
| **tiny** | ~39M | ~1 GB | ⚡⚡⚡⚡⚡ (~32x) | Testes rápidos, rascunhos, dispositivos modestos |
| **base** | ~74M | ~1 GB | ⚡⚡⚡⚡ (~16x) | **Recomendado para uso diário em CPU** |
| **small** | ~244M | ~2 GB | ⚡⚡⚡ (~6x) | Boa precisão para vocabulários técnicos |
| **medium** | ~769M | ~5 GB | ⚡⚡ (~2x) | Alta precisão para áudios com ruído |
| **large-v3** | ~1550M | ~10 GB | ⚡ (1x) | Precisão máxima para dublagem/legendagem profissional |

---

## 🐳 Docker (Opcional)

Se preferir rodar isolado em contêiner Docker:

```bash
docker compose up -d --build
```
Acesse `http://localhost:8000`.

---

## 🤝 Contribuindo

Contribuições são super bem-vindas! Veja as instruções no nosso [Guia de Contribuição](CONTRIBUTING.md).

Para reportar bugs ou sugerir recursos, utilize nossos formulários em [Issues](https://github.com/realkalashnikov/transcriber/issues).

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
