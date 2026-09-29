import threading
from typing import Optional
from fastapi import HTTPException
from app.core.config import settings
from app.engine.faster_whisper import get_audio_duration

class ConcurrencyGuard:
    """Controlador de concorrência global em thread para inferência Whisper."""

    _semaphore = threading.Semaphore(max(1, settings.max_concurrent_jobs))
    _active_jobs_count = 0
    _lock = threading.Lock()

    @classmethod
    def acquire(cls, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        acquired = cls._semaphore.acquire(blocking=blocking, timeout=timeout if timeout is not None else -1)
        if acquired:
            with cls._lock:
                cls._active_jobs_count += 1
        return acquired

    @classmethod
    def release(cls):
        with cls._lock:
            if cls._active_jobs_count > 0:
                cls._active_jobs_count -= 1
        cls._semaphore.release()

    @classmethod
    def get_stats(cls):
        with cls._lock:
            return {
                "max_concurrent_jobs": settings.max_concurrent_jobs,
                "active_jobs": cls._active_jobs_count
            }

def validate_upload_size(content_length: Optional[int], read_bytes: int):
    """Verifica tamanho em bytes contra o limite configurado."""
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if content_length and content_length > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede o limite máximo permitido de {settings.max_upload_size_mb}MB."
        )
    if read_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede o limite máximo permitido de {settings.max_upload_size_mb}MB."
        )

def validate_audio_duration(file_path: str):
    """Verifica duração do áudio em segundos contra o limite configurado."""
    if settings.max_audio_duration_seconds <= 0:
        return
    duration = get_audio_duration(file_path)
    if duration > settings.max_audio_duration_seconds:
        raise HTTPException(
            status_code=422,
            detail=f"Duração do áudio ({duration:.1f}s) excede o limite máximo permitido de {settings.max_audio_duration_seconds}s para esta instância."
        )
