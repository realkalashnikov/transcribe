import os
import uuid
import time
import shutil
from typing import Dict, Any, Optional
from pathlib import Path

from app.config import UPLOAD_DIR
from app.engine.base import BaseTranscriber, TranscriptionResult
from app.engine.faster_whisper import FasterWhisperTranscriber
from app.engine.cloud_apis import CloudTranscriber
from app.services.exporter import Exporter
from app.services.history import HistoryService

from app.engine.whisper_cpp import WhisperCppTranscriber

# Memória em tempo de execução dos status das tarefas
_JOBS: Dict[str, Dict[str, Any]] = {}

class TranscriberService:
    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        return _JOBS.get(job_id)

    @staticmethod
    def update_job(job_id: str, **kwargs):
        if job_id in _JOBS:
            _JOBS[job_id].update(kwargs)

    @staticmethod
    def execute_transcription(
        job_id: str,
        file_path: str,
        provider: str = "faster-whisper",
        model: Optional[str] = None,
        language: Optional[str] = None,
        task: str = "transcribe",
        api_key: Optional[str] = None,
        original_filename: Optional[str] = None
    ) -> TranscriptionResult:
        _JOBS[job_id] = {
            "id": job_id,
            "status": "processing",
            "progress": 5.0,
            "message": "Iniciando processamento...",
            "result": None,
            "error": None
        }

        def on_progress(pct: float, msg: str):
            TranscriberService.update_job(job_id, progress=pct, message=msg)

        try:
            provider_clean = (provider or "faster-whisper").lower().strip()

            if provider_clean in ["faster-whisper", "local"]:
                engine = FasterWhisperTranscriber(model_size=model or "base")
            elif provider_clean in ["whisper.cpp", "whisper_cpp"]:
                engine = WhisperCppTranscriber(model_size=model or "base")
            elif provider_clean in ["groq", "openai", "gemini"]:
                if not api_key:
                    raise ValueError(f"Chave de API obrigatória para o provedor {provider_clean}.")
                engine = CloudTranscriber(provider=provider_clean, api_key=api_key, model=model)
            else:
                raise ValueError(f"Provedor não suportado: {provider_clean}")

            result = engine.transcribe(
                file_path=file_path,
                language=language,
                task=task,
                progress_callback=on_progress
            )

            # Exportações pré-calculadas
            export_formats = {
                "txt": Exporter.to_txt(result),
                "srt": Exporter.to_srt(result),
                "vtt": Exporter.to_vtt(result),
                "json": Exporter.to_json(result)
            }

            result_dict = {
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
                ],
                "exports": export_formats
            }

            TranscriberService.update_job(
                job_id,
                status="completed",
                progress=100.0,
                message="Transcrição concluída!",
                result=result_dict
            )

            # Persiste no disco (JSON e arquivo de áudio) para nunca perder após reiniciar o servidor
            fname = original_filename or os.path.basename(file_path)
            HistoryService.save(job_id=job_id, filename=fname, result_dict=result_dict, audio_path=file_path)

            return result

        except Exception as e:
            TranscriberService.update_job(
                job_id,
                status="error",
                progress=0.0,
                message="Erro na transcrição",
                error=str(e)
            )
            raise e
        finally:
            # Remove arquivo temporário se desejar manter o disco limpo
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
