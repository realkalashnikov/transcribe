import os
import time
import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Request, Response
from fastapi.responses import PlainTextResponse, JSONResponse
import ctranslate2

from app.core.config import (
    UPLOAD_DIR,
    LOCAL_ENGINES,
    LOCAL_WHISPER_MODELS,
    CLOUD_PROVIDERS,
    SUPPORTED_LANGUAGES,
    settings
)
from app.services.transcriber import TranscriberService
from app.services.history import sanitize_session_id
from app.services.exporter import Exporter
from app.engine.faster_whisper import get_audio_duration

router = APIRouter(prefix="/api/v1", tags=["API v1 (Pública)"])
_START_TIME = time.time()

@router.get("/status")
def get_v1_status():
    """Endpoint de verificação de integridade e status da API v1."""
    return {
        "status": "online",
        "version": "1.1.0",
        "uptime_seconds": round(time.time() - _START_TIME, 2),
        "timestamp": time.time()
    }

@router.get("/info")
def get_v1_info():
    """Metadados completos da instância para clientes de API, bots e integrações."""
    cuda_available = ctranslate2.get_cuda_device_count() > 0
    return {
        "instance_name": settings.instance_name,
        "instance_mode": settings.instance_mode,
        "requires_auth": bool(settings.is_private and settings.access_pin),
        "limits": {
            "max_audio_duration_seconds": settings.max_audio_duration_seconds,
            "max_upload_size_mb": settings.max_upload_size_mb,
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "transcribe_rate_limit_per_minute": settings.transcribe_rate_limit_per_minute,
            "max_concurrent_jobs": settings.max_concurrent_jobs
        },
        "hardware": {
            "cuda_available": cuda_available,
            "recommended_device": "cuda" if cuda_available else "cpu"
        },
        "engines": LOCAL_ENGINES,
        "models": LOCAL_WHISPER_MODELS,
        "cloud_providers": CLOUD_PROVIDERS,
        "supported_languages": SUPPORTED_LANGUAGES
    }

@router.post("/transcribe")
async def v1_transcribe(
    request: Request,
    file: UploadFile = File(..., description="Arquivo de áudio ou vídeo para transcrição"),
    provider: str = Form("faster-whisper", description="Motor: faster-whisper, whisper.cpp, groq, openai, gemini"),
    model: Optional[str] = Form(None, description="Tamanho do modelo (tiny, base, small, medium, large-v3)"),
    language: Optional[str] = Form(None, description="Código de idioma (ex: pt, en) ou vazio para auto-detecção"),
    task: str = Form("transcribe", description="transcribe ou translate"),
    api_key: Optional[str] = Form(None, description="Chave de API se usar provedores de nuvem"),
    response_format: str = Form("json", description="Formato da resposta: json, text, srt, vtt"),
    x_session_id: Optional[str] = Header(None, description="ID de sessão isolada opcional")
):
    """
    Endpoint padronizado da API REST v1 para bots (Discord, Telegram), automações e desenvolvedores.
    Aceita arquivo de áudio via multipart/form-data e retorna a transcrição no formato desejado.
    """
    session_id = sanitize_session_id(x_session_id or request.cookies.get("session_id"))
    job_id = str(uuid.uuid4())
    temp_filename = f"v1_{job_id}_{file.filename}"
    file_path = str(UPLOAD_DIR / temp_filename)

    # 1. Valida tamanho do upload durante o streaming
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
                        detail=f"Arquivo excede o tamanho máximo de {settings.max_upload_size_mb}MB permitido por esta instância."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Valida duração máxima do áudio
    if settings.max_audio_duration_seconds > 0:
        duration = get_audio_duration(file_path)
        if duration > settings.max_audio_duration_seconds:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=422,
                detail=f"Duração do áudio ({duration:.1f}s) excede o limite máximo permitido de {settings.max_audio_duration_seconds}s para esta instância."
            )

    # 3. Executa transcrição
    try:
        result = TranscriberService.execute_transcription(
            job_id=job_id,
            file_path=file_path,
            provider=provider,
            model=model,
            language=language,
            task=task,
            api_key=api_key,
            original_filename=file.filename,
            session_id=session_id
        )

        fmt = (response_format or "json").lower().strip()
        if fmt == "text":
            return PlainTextResponse(Exporter.to_txt(result))
        elif fmt == "srt":
            return PlainTextResponse(Exporter.to_srt(result), media_type="text/plain")
        elif fmt == "vtt":
            return PlainTextResponse(Exporter.to_vtt(result), media_type="text/vtt")
        else:
            return {
                "id": job_id,
                "text": result.text,
                "language": result.language,
                "duration": result.duration,
                "model": result.model,
                "provider": result.provider,
                "segments": [
                    {
                        "id": s.id,
                        "start": s.start,
                        "end": s.end,
                        "text": s.text
                    }
                    for s in result.segments
                ]
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
