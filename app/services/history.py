import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import HISTORY_DIR

class HistoryService:
    @staticmethod
    def save(job_id: str, filename: str, result_dict: Dict[str, Any], audio_path: Optional[str] = None) -> None:
        """Salva a transcrição permanentemente no disco em formato JSON e preserva o arquivo de áudio para re-escuta."""
        audio_saved_name = None
        if audio_path and os.path.exists(audio_path):
            ext = os.path.splitext(audio_path)[1].lower() or ".mp3"
            dest_audio = HISTORY_DIR / f"{job_id}{ext}"
            try:
                shutil.copy2(audio_path, dest_audio)
                audio_saved_name = f"{job_id}{ext}"
            except Exception as e:
                print(f"Aviso ao salvar áudio no histórico: {e}")

        file_path = HISTORY_DIR / f"{job_id}.json"
        data = {
            "id": job_id,
            "filename": filename,
            "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "timestamp": datetime.now().timestamp(),
            "audio_file": audio_saved_name,
            **result_dict
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        """Retorna todas as transcrições salvas, ordenadas da mais recente para a mais antiga."""
        items = []
        if not HISTORY_DIR.exists():
            return items

        for file_path in HISTORY_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items.append({
                        "id": data.get("id"),
                        "filename": data.get("filename", "Sem nome"),
                        "saved_at": data.get("saved_at", ""),
                        "timestamp": data.get("timestamp", 0),
                        "duration": data.get("duration", 0),
                        "language": data.get("language", "auto"),
                        "provider": data.get("provider", "local"),
                        "model": data.get("model", ""),
                        "has_audio": bool(data.get("audio_file"))
                    })
            except Exception:
                continue

        # Ordena pelo timestamp decrescente
        items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return items

    @staticmethod
    def get(job_id: str) -> Optional[Dict[str, Any]]:
        """Obtém os dados completos de uma transcrição salva no disco."""
        file_path = HISTORY_DIR / f"{job_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def get_audio_path(job_id: str) -> Optional[Path]:
        """Localiza o arquivo de áudio associado ao job_id no histórico."""
        item = HistoryService.get(job_id)
        if item and item.get("audio_file"):
            p = HISTORY_DIR / item["audio_file"]
            if p.exists():
                return p
        # Busca por extensão
        for candidate in HISTORY_DIR.glob(f"{job_id}.*"):
            if candidate.suffix.lower() != ".json":
                return candidate
        return None

    @staticmethod
    def delete(job_id: str) -> bool:
        """Exclui a transcrição e qualquer arquivo de áudio associado."""
        success = False
        for p in HISTORY_DIR.glob(f"{job_id}.*"):
            try:
                os.remove(p)
                success = True
            except Exception:
                pass
        return success
