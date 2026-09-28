import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

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
