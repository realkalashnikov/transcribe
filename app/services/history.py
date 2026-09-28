import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import HISTORY_DIR

class HistoryService:
    @staticmethod
    def save(job_id: str, filename: str, result_dict: Dict[str, Any]) -> None:
        """Salva a transcrição permanentemente no disco em formato JSON."""
        file_path = HISTORY_DIR / f"{job_id}.json"
        data = {
            "id": job_id,
            "filename": filename,
            "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "timestamp": datetime.now().timestamp(),
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
                    # Versão compacta para listagem rápida
                    items.append({
                        "id": data.get("id"),
                        "filename": data.get("filename", "Sem nome"),
                        "saved_at": data.get("saved_at", ""),
                        "timestamp": data.get("timestamp", 0),
                        "duration": data.get("duration", 0),
                        "language": data.get("language", "auto"),
                        "provider": data.get("provider", "local"),
                        "model": data.get("model", "")
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
    def delete(job_id: str) -> bool:
        """Exclui uma transcrição salva do disco."""
        file_path = HISTORY_DIR / f"{job_id}.json"
        if file_path.exists():
            try:
                os.remove(file_path)
                return True
            except Exception:
                pass
        return False
