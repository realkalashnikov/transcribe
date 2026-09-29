# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.
O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [1.1.0] - 2026-09-29

### 🚀 Adicionado
- **Suporte a Instâncias Auto-Hospedadas & Públicas (Estilo Cobalt / Monochrome)**:
  - Novo módulo de configurações centralizadas em `app/core/config.py` com suporte completo a `.env` sem dependências externas.
  - Modos de instância configuráveis: `private` (uso fechado com PIN opcional), `public` (aberto para visitantes) e `byok` (*Bring Your Own Key*).
  - Parâmetros anti-abuso configuráveis: `MAX_AUDIO_DURATION_SECONDS` (padrão 5 min em público), `MAX_UPLOAD_SIZE_MB`, `MAX_CONCURRENT_JOBS` e limites de requisições.
- **Isolamento de Sessão & Privacidade Efêmera**:
  - Sessão única por visitante via cabeçalho/cookie `X-Session-ID` com sanitização estrita contra *directory traversal*.
  - Particionamento de diretórios de histórico por sessão em `exports/history/{session_id}/`, garantindo que nenhum visitante enxergue o histórico de outro.
  - Serviço de limpeza em segundo plano `CleanerService` (`app/services/cleaner.py`) que roda periodicamente para expirar e excluir áudios e transcrições antigos após 60 minutos em instâncias públicas.
- **Escudo de Segurança & Anti-Abuso**:
  - Middleware de Rate Limiting em memória (`app/middleware/rate_limit.py`) com janelas deslizantes por IP e Sessão, retornando HTTP 429 e cabeçalho `Retry-After`.
  - Middleware de Autenticação (`app/middleware/auth.py`) com suporte a PIN de acesso e proteção ativa contra ataques de força bruta (bloqueio temporário após 5 falhas consecutivas).
  - Controle de concorrência com semáforo em thread (`app/services/concurrency.py`) para evitar estouro de memória GPU/CPU.
  - Validação antecipada de tamanho de arquivo durante o streaming e validação de duração máxima via PyAV.
- **Túnel Cloudflare Integrado (Acesso Remoto & Celular)**:
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
