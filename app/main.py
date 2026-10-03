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
import hmac
from app.services.transcriber import TranscriberService
from app.services.history import HistoryService, sanitize_session_id
from app.services.cleaner import CleanerService
from app.services.tunnel import TunnelService
from app.services.concurrency import ConcurrencyGuard, save_and_validate_upload
from app.engine.faster_whisper import get_audio_duration
from app.middleware.rate_limit import RateLimiterMiddleware
from app.middleware.auth import AuthMiddleware, is_pin_locked, record_pin_failure, reset_pin_failures
from app.api.v1 import api_v1_router
from pydantic import BaseModel
from app.services.downloader import MediaDownloader, SSRFError
from app.services.llm_actions import LLMActionService

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

# Roteador da API REST v1
app.include_router(api_v1_router)

def resolve_session_id(x_session_id: Optional[str], request: Request) -> Optional[str]:
    """Obtém e valida o session_id de headers, cookies ou query parameters (para tags de áudio)."""
    cand = (
        x_session_id
        or request.cookies.get("session_id")
        or request.query_params.get("session_id")
    )
    return sanitize_session_id(cand)

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Transcribe Studio API ativa"}

@app.get("/health", tags=["Health Check"])
def health_check():
    """Health check endpoint para monitoramento e Docker."""
    return {"status": "ok", "mode": settings.instance_mode}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# Cache de capacidades de hardware na inicialização
try:
    _CUDA_AVAILABLE_CACHE = ctranslate2.get_cuda_device_count() > 0
except Exception:
    _CUDA_AVAILABLE_CACHE = False

@app.get("/api/info")
def get_system_info():
    """Retorna capacidades de hardware, provedores disponíveis e limites da instância de forma instantânea."""
    return {
        "cuda_available": _CUDA_AVAILABLE_CACHE,
        "device_recommended": "cuda" if _CUDA_AVAILABLE_CACHE else "cpu",
        "local_engines": LOCAL_ENGINES,
        "local_models": LOCAL_WHISPER_MODELS,
        "cloud_providers": CLOUD_PROVIDERS,
        "languages": SUPPORTED_LANGUAGES,
        "instance": settings.to_public_dict(),
        "concurrency": ConcurrencyGuard.get_stats()
    }

@app.get("/api/tunnel/info")
def get_tunnel_info():
    """Retorna status do túnel, links de acesso e rede local."""
    return TunnelService.get_info(port=settings.port)

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
    if not pin or not hmac.compare_digest(str(pin).strip(), settings.access_pin.strip()):
        count, lockout = record_pin_failure(client_ip)
        if lockout > 0:
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas incorretas de PIN. Acesso bloqueado temporariamente por 5 minutos."
            )
        raise HTTPException(status_code=401, detail="PIN de acesso incorreto.")

    reset_pin_failures(client_ip)
    return {"authenticated": True, "token": settings.access_pin, "mode": settings.instance_mode}

@app.post("/api/transcribe")
async def transcribe_file(
    request: Request,
    file: UploadFile = File(...),
    provider: str = Form("faster-whisper"),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    x_session_id: Optional[str] = Header(None)
):
    """Endpoint síncrono para transcrição com validação de quotas e isolamento de sessão."""
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

    session_id = resolve_session_id(x_session_id, request)
    job_id, file_path = await save_and_validate_upload(file)

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
            session_id=session_id,
            base_url=base_url
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
    prompt: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    x_session_id: Optional[str] = Header(None)
):
    """Endpoint assíncrono para processamento em background com acompanhamento e quotas."""
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

    session_id = resolve_session_id(x_session_id, request)
    clean_prompt = prompt.strip()[:500] if prompt and prompt.strip() else None
    job_id, file_path = await save_and_validate_upload(file)

    background_tasks.add_task(
        TranscriberService.execute_transcription,
        job_id=job_id,
        file_path=file_path,
        provider=provider,
        model=model,
        language=language,
        task=task,
        prompt=clean_prompt,
        api_key=api_key,
        original_filename=file.filename,
        session_id=session_id,
        base_url=base_url
    )

    return {"job_id": job_id, "filename": file.filename, "status": "queued"}

@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = TranscriberService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job

@app.get("/api/jobs/{job_id}/stream")
async def stream_job_status(job_id: str, request: Request):
    """Server-Sent Events (SSE) para stream de status em tempo real sem polling."""
    import asyncio
    import json
    from starlette.responses import StreamingResponse

    job = TranscriberService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    async def event_generator():
        last_progress = None
        last_status = None
        # Timeout de segurança: 30 minutos
        start_time = asyncio.get_event_loop().time()
        while True:
            if await request.is_disconnected():
                break

            current_job = TranscriberService.get_job(job_id)
            if not current_job:
                break

            progress = current_job.get("progress")
            status = current_job.get("status")

            # Emite evento apenas se houver mudança de estado ou na primeira iteração
            if progress != last_progress or status != last_status:
                last_progress = progress
                last_status = status
                payload = json.dumps(current_job)
                yield f"data: {payload}\n\n"

            if status in ["completed", "error"]:
                break

            if asyncio.get_event_loop().time() - start_time > 1800:
                break

            await asyncio.sleep(0.35)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

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

class UrlIngestRequest(BaseModel):
    url: str
    provider: str = "faster-whisper"
    model: Optional[str] = None
    language: Optional[str] = None
    task: str = "transcribe"
    prompt: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class SummarizeRequest(BaseModel):
    job_id: Optional[str] = None
    text: Optional[str] = None
    action: str = "summary"
    target_language: str = "pt"
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

class HistoryUpdateRequest(BaseModel):
    text: Optional[str] = None
    segments: Optional[list] = None

@app.post("/api/ingest/url")
async def ingest_url(
    req: UrlIngestRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    x_session_id: Optional[str] = Header(None)
):
    """Baixa áudio de URL pública (YouTube, etc.) com escudo anti-SSRF e enfileira transcrição."""
    prov_clean = (req.provider or "faster-whisper").lower().strip()
    if settings.is_byok:
        if prov_clean in ["faster-whisper", "local", "whisper.cpp", "whisper_cpp"]:
            raise HTTPException(
                status_code=400,
                detail="Esta instância opera no modo BYOK. Motores locais estão desabilitados."
            )
        if not req.api_key or not str(req.api_key).strip():
            raise HTTPException(
                status_code=400,
                detail="Chave de API obrigatória no modo BYOK."
            )

    session_id = resolve_session_id(x_session_id, request)

    try:
        media_info = MediaDownloader.download_url(req.url)
    except SSRFError as e:
        raise HTTPException(status_code=400, detail=f"Bloqueio de Segurança (SSRF): {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar URL: {e}")

    job_id = str(uuid.uuid4())
    file_path = media_info["file_path"]
    clean_title = media_info["title"] + Path(file_path).suffix

    clean_prompt = req.prompt.strip()[:500] if req.prompt and req.prompt.strip() else None

    # Registra o job inicial
    background_tasks.add_task(
        TranscriberService.execute_transcription,
        job_id=job_id,
        file_path=file_path,
        provider=req.provider,
        model=req.model,
        language=req.language,
        task=req.task,
        prompt=clean_prompt,
        api_key=req.api_key,
        original_filename=clean_title,
        session_id=session_id,
        base_url=req.base_url
    )

    return {
        "job_id": job_id,
        "filename": clean_title,
        "status": "queued",
        "duration": media_info.get("duration", 0),
        "source": "url"
    }

@app.post("/api/summarize")
async def summarize_transcript(
    req: SummarizeRequest,
    request: Request,
    x_session_id: Optional[str] = Header(None)
):
    """Executa ações com LLM (Resumo, Ata, Tópicos, Tradução) sobre uma transcrição."""
    text = req.text
    if not text and req.job_id:
        session_id = resolve_session_id(x_session_id, request)
        item = HistoryService.get(req.job_id, session_id=session_id)
        if not item:
            raise HTTPException(status_code=404, detail="Transcrição não encontrada no histórico.")
        text = item.get("text", "")

    if not text or not str(text).strip():
        raise HTTPException(status_code=400, detail="Texto vazio ou não fornecido.")

    try:
        res = LLMActionService.process_action(
            text=text,
            action=req.action,
            target_language=req.target_language,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
            base_url=req.base_url
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento LLM: {e}")

@app.put("/api/history/{job_id}")
def update_history_item(
    job_id: str,
    req: HistoryUpdateRequest,
    request: Request,
    x_session_id: Optional[str] = Header(None)
):
    """Atualiza o conteúdo de uma transcrição existente (Edição Inline)."""
    session_id = resolve_session_id(x_session_id, request)
    updated = HistoryService.update(
        job_id=job_id,
        updated_segments=req.segments,
        updated_text=req.text,
        session_id=session_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada para atualização.")
    return {"success": True, "item": updated}

class RomanizeRequest(BaseModel):
    text: Optional[str] = None
    language: Optional[str] = None
    segments: Optional[list] = None

@app.post("/api/romanize")
def romanize_transcript(req: RomanizeRequest):
    """Gera transliteração/romanização fonética para idiomas como Japonês, Chinês e Russo."""
    from app.services.transliteration import TransliterationService
    lang = req.language or "ja"
    rom_text = TransliterationService.romanize(req.text or "", language=lang)
    rom_segs = None
    if req.segments:
        rom_segs = TransliterationService.romanize_segments(req.segments, language=lang)
    return {
        "language": lang,
        "romanized_text": rom_text,
        "segments": rom_segs
    }

@app.get("/api/history/{job_id}/export/video")
def export_muxed_video(
    job_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    x_session_id: Optional[str] = Header(None)
):
    """Gera contêiner MP4 com legenda SRT embutida via stream mov_text."""
    from app.services.video_muxer import VideoMuxer
    session_id = resolve_session_id(x_session_id, request)
    item = HistoryService.get(job_id, session_id=session_id)
    if not item:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")

    audio_path = HistoryService.get_audio_path(job_id, session_id=session_id)
    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo original de mídia não encontrado para muxing")

    exports = item.get("exports") or {}
    srt_content = exports.get("srt")
    if not srt_content:
        raise HTTPException(status_code=400, detail="Legenda SRT indisponível para esta transcrição")

    try:
        muxed_path = VideoMuxer.mux_subtitles(str(audio_path), srt_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao embutir legendas: {e}")

    background_tasks.add_task(lambda p: os.path.exists(p) and os.remove(p), muxed_path)

    orig_name = item.get("filename") or "video"
    base_name = Path(orig_name).stem
    return FileResponse(
        muxed_path,
        media_type="video/mp4",
        filename=f"{base_name}_legendado.mp4"
    )
