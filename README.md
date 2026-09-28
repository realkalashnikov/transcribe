# 🎙️ Transcribe Studio

Sistema leve, rápido e moderno para transcrição de áudios e vídeos.

Permite transcrever arquivos diretamente no seu computador com **faster-whisper** (totalmente offline, sem custos e privado) ou, opcionalmente, via **APIs na Nuvem** (Groq Whisper, OpenAI Whisper ou Google Gemini) informando sua própria API key.

---

## 🚀 Como Executar no Windows (Sem Docker)

Você **não precisa de Docker** nem de **Node.js/npm**! Basta ter o Python instalado.

### Opção 1: Dois cliques
Dê dois cliques no arquivo:
```cmd
run.bat
```

### Opção 2: Pelo terminal
```bash
python run.py
```

O servidor iniciará em `http://localhost:8000` e seu navegador padrão será aberto automaticamente!

---

## 🛠️ Instalação das Dependências (Caso seja a primeira vez em outra máquina)

```bash
pip install -r requirements.txt
```

---

## ✨ Funcionalidades

- **100% Local com faster-whisper**:
  - Usa quantização `int8` otimizada para CPU ou `float16` com aceleração por GPU (se CUDA estiver disponível).
  - Modelos selecionáveis: `tiny`, `base` (recomendado), `small`, `medium`, `large-v3`, `large-v3-turbo`.
- **Nuvem Opcional (via API Key)**:
  - **Groq**: Whisper-large-v3 com velocidade ultrarrápida (transcreve áudios em segundos).
  - **OpenAI**: Whisper-1 oficial.
  - **Google Gemini**: Gemini 2.5 Flash / 1.5 Flash.
  - As chaves de API ficam salvas com segurança no `localStorage` do seu navegador.
- **Formatos de Entrada Suportados**:
  - MP3, WAV, M4A, OGG, FLAC, AAC, MP4, MKV, AVI, WebM, etc. (decodificação via PyAV, dispensando binários externos).
- **Processamento em Lote (Batch)**:
  - Arraste múltiplos arquivos de uma só vez; eles serão processados em fila com barra de progresso.
- **Exportação Imediata**:
  - **TXT**: Texto corrido limpo.
  - **SRT**: Arquivo de legendas para reprodutores de vídeo (VLC, YouTube, etc.).
  - **VTT**: Legendas para a web.
  - **JSON**: Dados brutos estruturados com timestamps.
  - **Copiar**: Copia todo o texto para a área de transferência com um clique.

---

## 🐳 Docker (Opcional)

Se futuramente desejar rodar em contêiner Docker:

```bash
docker compose up -d --build
```
Acesse `http://localhost:8000`.
