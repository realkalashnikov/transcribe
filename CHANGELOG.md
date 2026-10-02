# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.
O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [1.3.0] - 2026-10-02

### 🚀 Adicionado
- **Ingestão Direta por URL com Escudo Anti-SSRF** (`app/services/downloader.py`, `POST /api/ingest/url`):
  - Permite colar links diretos do YouTube, Twitter/X, SoundCloud e streams de áudio/vídeo para transcrição automática via `yt-dlp`.
  - Escudo de segurança anti-SSRF com resolução prévia de DNS e bloqueio rigoroso de redes privadas (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopbacks (`127.0.0.0/8`), link-local (`169.254.0.0/16`, cloud metadata AWS/GCP) e portas não padrão.
- **Resumo e Ações Pós-Transcrição com IA / LLMs** (`app/services/llm_actions.py`, `POST /api/summarize`):
  - Botões de um clique na interface: 📝 **Resumo Executivo**, 📋 **Ata & Próximos Passos**, 🎯 **Tópicos Principais**, 🌐 **Tradução Direta**.
  - Suporte multi-provedor nativo: Groq (`llama-3.3-70b-versatile`), Google Gemini (`gemini-2.5-flash`), OpenAI (`gpt-4o-mini`) e Ollama local (`llama3.2`) 100% offline.
  - Painel com renderização de resposta, destaque e botão para cópia instantânea.
- **Timestamps Clicáveis & Karaoke Word-Level em Tempo Real**:
  - Habilitação de timestamps a nível de palavra (`word_timestamps=True`) no faster-whisper.
  - O player de áudio integrado sincroniza a palavra exata falada em tempo real com realce luminoso suave.
  - Clicar em qualquer palavra ou timestamp pula imediatamente o player para o trecho exato correspondente.
- **Edição Inline de Transcrição no Navegador com Salvamento Permanente**:
  - Correção de textos e termos técnicos diretamente na interface web via `contenteditable`.
  - Botão *"Salvar Revisão"* que persiste as alterações no disco permanentemente via `PUT /api/history/{job_id}` e recalcula automaticamente as exportações TXT, SRT, VTT e JSON.
- **Romanização / Transliteração Fonética para Idiomas Globais** (`app/services/transliteration.py`, `POST /api/romanize`):
  - Suporte para Japonês (Romaji Hepburn via `pykakasi`), Chinês (Pinyin com acentos tonais via `pypinyin`) e Cirílico (Russo/Ucraniano).
  - Botão de alternância *"Romanização"* que exibe a leitura fonética em itálico abaixo dos ideogramas originais.
- **Mux de Legendas em Vídeo MP4 sem Perda** (`app/services/video_muxer.py`, `GET /api/history/{job_id}/export/video`):
  - Integração com `imageio-ffmpeg` para embutir legendas SRT como stream `mov_text` em contêineres MP4 por cópia direta de stream sem recodificação de vídeo.
- **Nova Suite de Testes Automatizados** (`test_advanced_features.py`):
  - Testes cobrindo anti-SSRF, ações LLM, edição inline no disco, romanização fonética e detecção de muxer de vídeo.

---

## [1.2.0] - 2026-09-29

### 🚀 Adicionado
- **Menu Interativo de Terminal (CLI Moderna)** (`app/core/cli_menu.py`):
  - Interface visual no terminal com cores ANSI inspirada em consoles modernos.
  - Cabeçalho ciano com sublinhado (`🗂 Transcribe Studio — Menu Principal`).
  - Navegação fluida com as setas do teclado `↑` e `↓` com barra azul de seleção ativa e marcadores em diamante `◈`.
  - Confirmação com tecla `Enter` e suporte a atalhos numéricos diretos (`1`, `2`, `3`, `4`).
  - Opção de encerramento em vermelho (`✕ Sair`) e tratamento elegante de `Ctrl+C` e `Esc`.
  - Implementação pura sem dependências externas, usando `msvcrt` nativo no Windows e modo raw com suporte a modo de aplicação cursor (SS3 / `\x1bOA`, `\x1bOB`) em POSIX.
  - Proteção contra quebra de linha e desincronização de cursor em janelas de terminal estreitas com dicas e larguras adaptativas.
  - Integração perfeita em `run.py` (acionado automaticamente ao executar sem flags em terminal interativo) e repasse unificado direto em `run.bat`.

### 🐛 Corrigido
- **Blindagem do PyAV e Correção no CI GitHub Actions**:
  - Adicionado `av>=11.0.0` explicitamente no `requirements.txt` para assegurar suporte ao argumento `metadata_errors`.
  - Implementado wrapper defensivo em `av.open` no módulo `app/engine/faster_whisper.py` para capturar `TypeError` incondicionalmente quando `metadata_errors` for fornecido em ambientes legados e realizar fallback automático sem quebras.
  - Adicionados testes automatizados abrangentes do CLI Menu e do fallback de `av.open` (`test_cli_menu.py`) cobrindo 16 cenários unitários integrados ao pipeline de CI no GitHub Actions.

---

## [1.1.0] - 2026-09-29

### 🚀 Adicionado
- **Suporte a Instâncias Auto-Hospedadas (VPS com Domínio ou Túnel Cloudflare)**:
  - Novo módulo de configurações centralizadas em `app/core/config.py` com suporte completo a `.env` sem dependências externas.
  - Modos de instância configuráveis: `private` (uso pessoal com PIN opcional), `public` (aberto para amigos/rede) e `byok` (*Bring Your Own Key*).
  - Parâmetros anti-abuso configuráveis: `MAX_AUDIO_DURATION_SECONDS`, `MAX_UPLOAD_SIZE_MB`, `MAX_CONCURRENT_JOBS` e limites de requisições.
  - Hospedagem nativa em VPS: basta rodar `python run.py --public` ouvindo em `0.0.0.0:8000` e apontar o domínio. O Cloudflare Tunnel é uma ferramenta estritamente opcional (`--tunnel`) para quem está no PC de casa sem IP público.
- **Histórico Persistente com Isolamento Silencioso (Zero Burocracia)**:
  - Cada visitante/dispositivo possui seu identificador único no `localStorage` (`session_id`).
  - Cada usuário acessa apenas suas próprias transcrições e áudios, gravados permanentemente no servidor sem serem excluídos após 1 hora.
  - Nenhuma exigência de login, email ou senhas burocráticas para amigos.
- **Escudo de Segurança & Anti-Abuso**:
  - Middleware de Rate Limiting em memória (`app/middleware/rate_limit.py`) ancorado no IP real do cliente.
  - Middleware de Autenticação (`app/middleware/auth.py`) com suporte a PIN opcional.
  - Controle de concorrência com semáforo em thread (`app/services/concurrency.py`) para evitar estouro de memória GPU/CPU.
  - Validação antecipada de tamanho de arquivo durante o streaming e validação de duração máxima via PyAV.
- **Túnel Cloudflare Opcional (Para Celular e Casa sem IP Fixo)**:
  - Módulo `TunnelService` (`app/services/tunnel.py`) com download automático do binário oficial `cloudflared` caso não esteja instalado.
  - Descoberta automática de IP local da máquina na rede Wi-Fi / Ethernet via socket UDP.
  - Inicialização de túnel rápido HTTPS temporário (`*.trycloudflare.com`) sem necessidade de conta ou abertura de portas no roteador.
  - Gerenciamento seguro do ciclo de vida do processo com encerramento automático em `atexit`.
  - Novos argumentos de linha de comando em `run.py`: `--public`, `--share`, `--tunnel`, `--pin`, `--mode`.
  - Novo menu interativo no script inicializador `run.bat`.
- **API REST Pública Padronizada (`/api/v1`)**:
  - `POST /api/v1/transcribe`: Endpoint público aceitando multipart/form-data e múltiplos formatos de retorno (`json`, `text`, `srt`, `vtt`).
  - `GET /api/v1/info`: Metadados da instância (status, quotas ativas, hardware CUDA/CPU e modelos disponíveis).
  - `GET /api/v1/status`: Health check rápido com uptime e versão.
  - `GET /api/tunnel/info`: Informações de rede local e status do túnel para a interface e clientes externos.
- **Interface Web & Responsividade Mobile**:
  - Badges informativos no topo da interface com modo da instância, limites de tempo e aceleração de hardware.
  - Botão de "Acesso Remoto / Celular" abrindo modal com abas para Internet (Túnel HTTPS) e Wi-Fi Local.
  - Gerador leve e autônomo de QR Code em SVG puro (`app/static/js/qrcode.js`) 100% offline sem CDNs externas.
  - Suporte a "Login com 1 Toque": ao escanear o QR Code, o parâmetro `?pin=` é capturado, autenticado via `/api/auth/verify` e limpo da barra de endereços do navegador.
  - Modal de autenticação por PIN quando acessando uma instância protegida.
  - Redesign responsivo para telas móveis (360px a 900px), botões touch-friendly com área mínima de 44px e scrubber de áudio otimizado para toque.

### 🛡️ Segurança & Blindagem Anti-Abuso
- **Sanitização Estrita de Job ID & Prevenção contra Injeção de Curingas**: Validação estrita por regex `^[a-zA-Z0-9_-]{1,64}$` impedindo que curingas (`*`) ou sequências de path traversal apaguem ou acessem dados indevidos.
- **Preservação de Dados do Host**: O `CleanerService` atua exclusivamente sobre subdiretórios de sessões efêmeras em instâncias públicas, garantindo que o histórico permanente do proprietário na raiz de `exports/history/` nunca seja excluído acidentalmente.
- **Unificação Inteligente em Modo Privado**: No modo privado, o histórico é compartilhado de forma transparente entre todos os dispositivos do proprietário (Desktop, Celular, etc.), enquanto no modo público há particionamento estrito com zero vazamento entre visitantes.
- **Defesa contra Ataques de Temporização (*Timing Attacks*)**: Comparação de PIN realizada em tempo constante com `hmac.compare_digest`.
- **Suporte ao Header `Authorization: Bearer <pin>`**: Permite que ferramentas de automação, scripts e bots consumam a API REST v1 de forma padronizada.
- **Prevenção contra Evasão de Rate Limit por Rotação de Sessão**: Rate limiter ancorado no endereço IP do cliente (`cf-connecting-ip`, `x-forwarded-for` ou socket), impossibilitando que atacantes burlem limites forjando IDs de sessão aleatórios.
- **Validação de Upload Aprimorada**: Rejeição imediata de arquivos vazios (0 bytes), sanitização de nomes de arquivos contra directory traversal e proteção de disco contra uploads gigantescos durante o streaming.
- **Aplicação Estrita do Modo BYOK (*Bring Your Own Key*)**: Bloqueio ativo no backend e na interface de motores locais no modo BYOK, exigindo obrigatoriamente chave de API própria para provedores de nuvem (Groq/OpenAI/Gemini).
- **Gerador de QR Code 100% Conforme ISO/IEC 18004**: Implementação matemática completa em JavaScript com GF(256), código corretor de erros Reed-Solomon e bits BCH, garantindo leitura instantânea por qualquer câmera de smartphone nativa.
- **Playback de Áudio com Autenticação e Sessão**: Suporte a tokens via cookies e query parameters, viabilizando reprodução contínua em tags `<audio>` nativas do HTML5 mesmo com proteção por PIN ou sessões isoladas ativas.

---

## [1.0.0] - 2026-09-28

### 🚀 Inicial
- Interface inicial com suporte a faster-whisper e whisper.cpp.
- Integração com provedores em nuvem: Groq, OpenAI e Google Gemini.
- Player de áudio integrado com destaque de minutagem em tempo real.
- Exportações para formatos TXT, SRT, VTT e JSON.
