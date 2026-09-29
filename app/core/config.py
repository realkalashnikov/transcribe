import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
HISTORY_DIR = EXPORT_DIR / "history"
BIN_DIR = BASE_DIR / "bin"

# Garante a existência dos diretórios fundamentais
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)

def load_dotenv(dotenv_path: Optional[Path] = None):
    """Lê arquivo .env simples sem dependências externas."""
    path = dotenv_path or (BASE_DIR / ".env")
    if not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"[Aviso] Falha ao ler .env: {e}")

# Carrega .env se presente
load_dotenv()

class Settings:
    """Configurações centralizadas com suporte a variáveis de ambiente e sobrescritas de CLI."""

    def __init__(self):
        # Modo de Instância: 'private' | 'public' | 'byok'
        self.instance_mode: str = os.getenv("INSTANCE_MODE", "private").lower().strip()
        if self.instance_mode not in ["private", "public", "byok"]:
            self.instance_mode = "private"

        self.instance_name: str = os.getenv("INSTANCE_NAME", "Transcribe Studio")
        self.access_pin: Optional[str] = os.getenv("ACCESS_PIN", None)
        if self.access_pin:
            self.access_pin = self.access_pin.strip()

        # Limites Anti-Abuso
        default_max_duration = 300 if self.instance_mode in ["public", "byok"] else 7200
        self.max_audio_duration_seconds: int = int(os.getenv("MAX_AUDIO_DURATION_SECONDS", str(default_max_duration)))
        
        default_max_upload = 50 if self.instance_mode in ["public", "byok"] else 500
        self.max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", str(default_max_upload)))

        self.max_concurrent_jobs: int = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))
        self.rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
        self.transcribe_rate_limit_per_minute: int = int(os.getenv("TRANSCRIBE_RATE_LIMIT_PER_MINUTE", "5"))

        # Limpeza Efêmera
        self.cleanup_expire_minutes: int = int(os.getenv("CLEANUP_EXPIRE_MINUTES", "60"))
        self.cleanup_interval_seconds: int = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "300"))

        # Host e Porta
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))

        # Cloudflare Tunnel
        self.enable_tunnel: bool = os.getenv("ENABLE_TUNNEL", "false").lower() in ["true", "1", "yes"]

    @property
    def is_public(self) -> bool:
        return self.instance_mode in ["public", "byok"]

    @property
    def is_byok(self) -> bool:
        return self.instance_mode == "byok"

    @property
    def is_private(self) -> bool:
        return self.instance_mode == "private"

    def to_public_dict(self) -> Dict[str, Any]:
        """Metadados seguros da instância para exibição pública e APIs externas."""
        return {
            "instance_name": self.instance_name,
            "instance_mode": self.instance_mode,
            "requires_auth": bool(self.is_private and self.access_pin),
            "max_audio_duration_seconds": self.max_audio_duration_seconds,
            "max_upload_size_mb": self.max_upload_size_mb,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "cleanup_expire_minutes": self.cleanup_expire_minutes if self.is_public else None
        }

settings = Settings()

# Motores locais suportados
LOCAL_ENGINES = [
    {"id": "faster-whisper", "name": "Faster-Whisper (Python / CTranslate2 - Recomendado)"},
    {"id": "whisper.cpp", "name": "Whisper.cpp (C++ Otimizado / GGML)"}
]

# Modelos suportados no whisper local
LOCAL_WHISPER_MODELS = [
    {"id": "tiny", "name": "Tiny (Mais rápido, ~39M params, ~1GB RAM)"},
    {"id": "base", "name": "Base (Equilíbrio rápido, ~74M params, ~1GB RAM)"},
    {"id": "small", "name": "Small (Boa precisão, ~244M params, ~2GB RAM)"},
    {"id": "medium", "name": "Medium (Alta precisão, ~769M params, ~5GB RAM)"},
    {"id": "large-v3", "name": "Large-v3 (Precisão máxima, ~1550M params, ~10GB RAM)"},
    {"id": "large-v3-turbo", "name": "Large-v3-Turbo (Precisão máxima acelerada)"}
]

# Provedores de API em Nuvem suportados
CLOUD_PROVIDERS = [
    {
        "id": "groq",
        "name": "Groq (Whisper-large-v3 ultra-rápido)",
        "models": ["whisper-large-v3", "whisper-large-v3-turbo", "distil-whisper-large-v3-en"],
        "default_model": "whisper-large-v3-turbo",
        "doc_url": "https://console.groq.com/keys"
    },
    {
        "id": "openai",
        "name": "OpenAI (Whisper-1 oficial)",
        "models": ["whisper-1"],
        "default_model": "whisper-1",
        "doc_url": "https://platform.openai.com/api-keys"
    },
    {
        "id": "gemini",
        "name": "Google Gemini (Gemini 2.5 Flash / 1.5 Flash)",
        "models": ["gemini-2.5-flash", "gemini-1.5-flash"],
        "default_model": "gemini-2.5-flash",
        "doc_url": "https://aistudio.google.com/app/apikey"
    }
]

# Idiomas comuns para facilidade de seleção (ou detecção automática)
SUPPORTED_LANGUAGES = [
    {"code": "", "name": "Detecção Automática"},
    {"code": "pt", "name": "Português"},
    {"code": "en", "name": "Inglês"},
    {"code": "es", "name": "Espanhol"},
    {"code": "fr", "name": "Francês"},
    {"code": "de", "name": "Alemão"},
    {"code": "it", "name": "Italiano"},
    {"code": "ja", "name": "Japonês"},
    {"code": "zh", "name": "Chinês"},
    {"code": "ru", "name": "Russo"}
]
