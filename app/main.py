import os
import sys
import uuid
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager

# Corrige aviso nativo do asyncio no Windows (WinError 10054) quando o navegador encerra streaming de áudio
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
        def _silent_call_connection_lost(self, exc=None):
            try:
                _orig_call_connection_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass
        _ProactorBasePipeTransport._call_connection_lost = _silent_call_connection_lost
    except Exception:
        pass

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Response, Request, Header
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import ctranslate2

from app.core.config import (
    BASE_DIR,
    UPLOAD_DIR,
    LOCAL_ENGINES,
    LOCAL_WHISPER_MODELS,
    CLOUD_PROVIDERS,
    SUPPORTED_LANGUAGES,
    settings
)
from app.services.transcriber import TranscriberService
from app.services.history import HistoryService, sanitize_session_id
from app.services.cleaner import CleanerService
from app.services.concurrency import ConcurrencyGuard, validate_upload_size, validate_audio_duration
from app.engine.faster_whisper import get_audio_duration
from app.middleware.rate_limit import RateLimiterMiddleware
from app.middleware.auth import AuthMiddleware, is_pin_locked, record_pin_failure, reset_pin_failures

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o serviço de limpeza periódica de uploads e histórico efêmero
    CleanerService.start()
    yield
    # Encerra graciosamente
    CleanerService.stop()

app = FastAPI(
    title="Transcribe Studio",
    description="Interface de transcrição rápida com faster-whisper e APIs na Nuvem",
    version="1.1.0",
    lifespan=lifespan
)

# Ordem dos Middlewares (Starlette executa em ordem inversa de adição):
# 1. CORS -> 2. Rate Limiting -> 3. Auth por PIN
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montagem de arquivos estáticos
STATIC_DIR = BASE_DIR / "app" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def resolve_session_id(x_session_id: Optional[str], request: Request) -> Optional[str]:
    """Obtém e valida o session_id de headers ou cookies."""
    cand = x_session_id or request.cookies.get("session_id")
    return sanitize_session_id(cand)

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Transcribe Studio API ativa"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/api/info")
def get_system_info():
    """Retorna capacidades de hardware, provedores disponíveis e limites da instância."""
    cuda_available = ctranslate2.get_cuda_device_count() > 0
    return {
        "cuda_available": cuda_available,
        "device_recommended": "cuda" if cuda_available else "cpu",
        "local_engines": LOCAL_ENGINES,
        "local_models": LOCAL_WHISPER_MODELS,
        "cloud_providers": CLOUD_PROVIDERS,
        "languages": SUPPORTED_LANGUAGES,
        "instance": settings.to_public_dict(),
        "concurrency": ConcurrencyGuard.get_stats()
    }

@app.post("/api/auth/verify")
async def verify_auth(request: Request):
    """Valida PIN de acesso e fornece token de sessão."""
    client_ip = request.client.host if request.client else "unknown"
    locked, remaining = is_pin_locked(client_ip)
    if locked:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas incorretas. Tente novamente em {remaining} segundos."
        )

    if not settings.is_private or not settings.access_pin:
        return {"authenticated": True, "mode": settings.instance_mode}

    data = {}
    try:
        data = await request.json()
    except Exception:
        pass

    pin = data.get("pin") or request.query_params.get("pin")
    if not pin or str(pin).strip() != settings.access_pin.strip():
        count, lockout = record_pin_failure(client_ip)
        if lockout > 0:
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas incorretas de PIN. Acesso bloqueado temporariamente por 5 minutos."
            )
        raise HTTPException(status_code=401, detail="PIN de acesso incorreto.")

    reset_pin_failures(client_ip)
    return {"authenticated": True, "token": settings.access_pin, "mode": settings.instance_mode}

async def _save_and_validate_upload(file: UploadFile) -> str:
    """Salva o upload em disco validando tamanho máximo e duração do áudio."""
    job_id = str(uuid.uuid4())
    temp_filename = f"{job_id}_{file.filename}"
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

    # Validação de duração máxima
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

@app.post("/api/transcribe")
async def transcribe_file(
    request: Request,
    file: UploadFile = File(...),
    provider: str = Form("faster-whisper"),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    api_key: Optional[str] = Form(None),
    x_session_id: Optional[str] = Header(None)
):
    """Endpoint síncrono para transcrição com validação de quotas e isolamento de sessão."""
    session_id = resolve_session_id(x_session_id, request)
    job_id, file_path = await _save_and_validate_upload(file)

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

        job_data = TranscriberService.get_job(job_id)
        return job_data["result"]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs")
async def create_transcription_job(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    provider: str = Form("faster-whisper"),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    api_key: Optional[str] = Form(None),
    x_session_id: Optional[str] = Header(None)
):
    """Endpoint assíncrono para processamento em background com acompanhamento e quotas."""
    session_id = resolve_session_id(x_session_id, request)
    job_id, file_path = await _save_and_validate_upload(file)

    background_tasks.add_task(
        TranscriberService.execute_transcription,
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

    return {"job_id": job_id, "filename": file.filename, "status": "queued"}

@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = TranscriberService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job

@app.get("/api/history")
def get_history(request: Request, x_session_id: Optional[str] = Header(None)):
    """Retorna transcrições salvas respeitando o isolamento da sessão do usuário."""
    session_id = resolve_session_id(x_session_id, request)
    return HistoryService.list_all(session_id=session_id)

@app.get("/api/history/{job_id}")
def get_history_item(job_id: str, request: Request, x_session_id: Optional[str] = Header(None)):
    """Retorna transcrição completa do histórico no escopo da sessão."""
    session_id = resolve_session_id(x_session_id, request)
    item = HistoryService.get(job_id, session_id=session_id)
    if not item:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada no histórico")
    return item

@app.get("/api/history/{job_id}/audio")
def get_history_audio(job_id: str, request: Request, x_session_id: Optional[str] = Header(None)):
    """Retorna arquivo de áudio para playback no escopo da sessão."""
    session_id = resolve_session_id(x_session_id, request)
    audio_path = HistoryService.get_audio_path(job_id, session_id=session_id)
    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado para esta transcrição")
    
    ext = audio_path.suffix.lower()
    media_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
        ".mp4": "video/mp4"
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return FileResponse(str(audio_path), media_type=media_type)

@app.delete("/api/history/{job_id}")
def delete_history_item(job_id: str, request: Request, x_session_id: Optional[str] = Header(None)):
    """Remove transcrição do histórico no escopo da sessão."""
    session_id = resolve_session_id(x_session_id, request)
    success = HistoryService.delete(job_id, session_id=session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Não foi possível excluir o item do histórico")
    return {"success": True, "message": "Item removido do histórico"}
