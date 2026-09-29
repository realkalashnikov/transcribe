"""
Backward-compatibility proxy for app.core.config.
"""
from app.core.config import (
    BASE_DIR,
    UPLOAD_DIR,
    EXPORT_DIR,
    HISTORY_DIR,
    BIN_DIR,
    Settings,
    settings,
    LOCAL_ENGINES,
    LOCAL_WHISPER_MODELS,
    CLOUD_PROVIDERS,
    SUPPORTED_LANGUAGES,
    load_dotenv
)

__all__ = [
    "BASE_DIR",
    "UPLOAD_DIR",
    "EXPORT_DIR",
    "HISTORY_DIR",
    "BIN_DIR",
    "Settings",
    "settings",
    "LOCAL_ENGINES",
    "LOCAL_WHISPER_MODELS",
    "CLOUD_PROVIDERS",
    "SUPPORTED_LANGUAGES",
    "load_dotenv"
]
