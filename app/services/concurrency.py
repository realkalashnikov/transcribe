import os
import re
import uuid
import threading
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from app.core.config import UPLOAD_DIR, settings
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

async def save_and_validate_upload(file: UploadFile, prefix: str = "") -> Tuple[str, str]:
    """
    Salva o upload em disco com segurança:
    1. Previne directory traversal sanitizando o nome do arquivo.
    2. Rejeita arquivos vazios (0 bytes) retornando HTTP 400.
    3. Valida tamanho máximo durante o streaming (evita DoS por esgotamento de disco).
    4. Valida duração máxima do áudio contra o limite configurado.
    """
    job_id = str(uuid.uuid4())
    raw_name = Path(file.filename).name if file.filename else "audio.mp3"
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", raw_name)
    if not safe_name:
        safe_name = "audio.mp3"

    pfx = f"{prefix}_" if prefix else ""
    temp_filename = f"{pfx}{job_id}_{safe_name}"
    file_path = str(UPLOAD_DIR / temp_filename)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    total_bytes = 0

    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    buffer.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Arquivo excede o tamanho máximo permitido de {settings.max_upload_size_mb}MB para esta instância."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

    if total_bytes == 0:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail="O arquivo enviado está vazio (0 bytes).")

    if settings.max_audio_duration_seconds > 0:
        duration = get_audio_duration(file_path)
        if duration > settings.max_audio_duration_seconds:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=422,
                detail=f"Duração do áudio ({duration:.1f}s) excede o limite máximo permitido de {settings.max_audio_duration_seconds}s para esta instância."
            )

    return job_id, file_path
