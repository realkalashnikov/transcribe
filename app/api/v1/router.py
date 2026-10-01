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
from app.services.concurrency import save_and_validate_upload

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
    prompt: Optional[str] = Form(None, description="Vocabulário custom, termos técnicos ou contexto inicial (até 500 caracteres)"),
    api_key: Optional[str] = Form(None, description="Chave de API se usar provedores de nuvem"),
    response_format: str = Form("json", description="Formato da resposta: json, text, srt, vtt"),
    x_session_id: Optional[str] = Header(None, description="ID de sessão isolada opcional")
):
    """
    Endpoint padronizado da API REST v1 para bots (Discord, Telegram), automações e desenvolvedores.
    Aceita arquivo de áudio via multipart/form-data e retorna a transcrição no formato desejado.
    """
    prov_clean = (provider or "faster-whisper").lower().strip()
    if settings.is_byok:
        if prov_clean in ["faster-whisper", "local", "whisper.cpp", "whisper_cpp"]:
            raise HTTPException(
                status_code=400,
                detail="Esta instância opera no modo BYOK (Bring Your Own Key). Motores locais estão desabilitados pelo administrador. Selecione um provedor de Nuvem e forneça sua própria chave de API."
            )
        if not api_key or not str(api_key).strip():
            raise HTTPException(
                status_code=400,
                detail="Chave de API obrigatória no modo BYOK."
            )

    session_id = sanitize_session_id(
        x_session_id or request.cookies.get("session_id") or request.query_params.get("session_id")
    )
    clean_prompt = prompt.strip()[:500] if prompt and prompt.strip() else None
    job_id, file_path = await save_and_validate_upload(file, prefix="v1")

    # 3. Executa transcrição
    try:
        result = TranscriberService.execute_transcription(
            job_id=job_id,
            file_path=file_path,
            provider=provider,
            model=model,
            language=language,
            task=task,
            prompt=clean_prompt,
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
