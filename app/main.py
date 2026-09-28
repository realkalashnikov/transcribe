import os
import uuid
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import ctranslate2

from app.config import (
    BASE_DIR,
    UPLOAD_DIR,
    LOCAL_ENGINES,
    LOCAL_WHISPER_MODELS,
    CLOUD_PROVIDERS,
    SUPPORTED_LANGUAGES
)
from app.services.transcriber import TranscriberService

app = FastAPI(
    title="Transcribe Studio",
    description="Interface de transcrição rápida com faster-whisper e APIs na Nuvem",
    version="1.0.0"
)

# CORS liberado para chamadas locais
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

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Transcribe Studio API ativa"}

@app.get("/api/info")
def get_system_info():
    cuda_available = ctranslate2.get_cuda_device_count() > 0
    return {
        "cuda_available": cuda_available,
        "device_recommended": "cuda" if cuda_available else "cpu",
        "local_engines": LOCAL_ENGINES,
        "local_models": LOCAL_WHISPER_MODELS,
        "cloud_providers": CLOUD_PROVIDERS,
        "languages": SUPPORTED_LANGUAGES
    }

@app.post("/api/transcribe")
async def transcribe_file(
    file: UploadFile = File(...),
    provider: str = Form("faster-whisper"),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    api_key: Optional[str] = Form(None)
):
    """
    Endpoint síncrono direto para transcrição de um arquivo.
    """
    job_id = str(uuid.uuid4())
    temp_filename = f"{job_id}_{file.filename}"
    file_path = str(UPLOAD_DIR / temp_filename)

    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB por pedaço
                buffer.write(chunk)

        result = TranscriberService.execute_transcription(
            job_id=job_id,
            file_path=file_path,
            provider=provider,
            model=model,
            language=language,
            task=task,
            api_key=api_key
        )

        job_data = TranscriberService.get_job(job_id)
        return job_data["result"]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs")
async def create_transcription_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    provider: str = Form("faster-whisper"),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    api_key: Optional[str] = Form(None)
):
    """
    Endpoint assíncrono para processamento em segundo plano com acompanhamento de progresso.
    """
    job_id = str(uuid.uuid4())
    temp_filename = f"{job_id}_{file.filename}"
    file_path = str(UPLOAD_DIR / temp_filename)

    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    # Inicia tarefa em background
    background_tasks.add_task(
        TranscriberService.execute_transcription,
        job_id=job_id,
        file_path=file_path,
        provider=provider,
        model=model,
        language=language,
        task=task,
        api_key=api_key
    )

    return {"job_id": job_id, "filename": file.filename, "status": "queued"}

@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = TranscriberService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job
