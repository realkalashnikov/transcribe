import os
import re
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.config import HISTORY_DIR, settings

def sanitize_session_id(session_id: Optional[str]) -> Optional[str]:
    """Valida e sanitiza o session_id para prevenir directory traversal."""
    if not session_id:
        return None
    session_clean = str(session_id).strip()
    if re.match(r"^[a-zA-Z0-9_-]{4,64}$", session_clean):
        return session_clean
    return None

def get_session_dir(session_id: Optional[str] = None) -> Path:
    """Retorna o diretório de histórico correspondente à sessão ou raiz."""
    safe_session = sanitize_session_id(session_id)
    if safe_session:
        target_dir = HISTORY_DIR / safe_session
    elif settings.is_public:
        target_dir = HISTORY_DIR / "_anonymous"
    else:
        target_dir = HISTORY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir

class HistoryService:
    @staticmethod
    def save(
        job_id: str,
        filename: str,
        result_dict: Dict[str, Any],
        audio_path: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Salva a transcrição no disco em formato JSON e preserva o arquivo de áudio no escopo da sessão."""
        target_dir = get_session_dir(session_id)
        audio_saved_name = None

        if audio_path and os.path.exists(audio_path):
            ext = os.path.splitext(audio_path)[1].lower() or ".mp3"
            dest_audio = target_dir / f"{job_id}{ext}"
            try:
                shutil.copy2(audio_path, dest_audio)
                audio_saved_name = f"{job_id}{ext}"
            except Exception as e:
                print(f"[Aviso] Falha ao salvar áudio no histórico: {e}")

        file_path = target_dir / f"{job_id}.json"
        data = {
            "id": job_id,
            "filename": filename,
            "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "timestamp": datetime.now().timestamp(),
            "audio_file": audio_saved_name,
            "session_id": sanitize_session_id(session_id),
            **result_dict
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def list_all(session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna todas as transcrições salvas para a sessão especificada, ordenadas da mais recente para a mais antiga."""
        items = []
        target_dir = get_session_dir(session_id)
        if not target_dir.exists():
            return items

        for file_path in target_dir.glob("*.json"):
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
    def get(job_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Obtém os dados completos de uma transcrição salva no escopo da sessão."""
        target_dir = get_session_dir(session_id)
        file_path = target_dir / f"{job_id}.json"
        
        # Se não achou na sessão e o modo for privado (não público), tenta na raiz
        if not file_path.exists() and not settings.is_public and target_dir != HISTORY_DIR:
            fallback = HISTORY_DIR / f"{job_id}.json"
            if fallback.exists():
                file_path = fallback

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def get_audio_path(job_id: str, session_id: Optional[str] = None) -> Optional[Path]:
        """Localiza o arquivo de áudio associado ao job_id no escopo da sessão."""
        target_dir = get_session_dir(session_id)
        item = HistoryService.get(job_id, session_id=session_id)
        if item and item.get("audio_file"):
            p = target_dir / item["audio_file"]
            if p.exists():
                return p
            # Fallback se for privado
            if not settings.is_public:
                fallback_p = HISTORY_DIR / item["audio_file"]
                if fallback_p.exists():
                    return fallback_p

        # Busca por extensão dentro do target_dir
        for candidate in target_dir.glob(f"{job_id}.*"):
            if candidate.suffix.lower() != ".json":
                return candidate

        # Fallback na raiz apenas se for privado
        if not settings.is_public and target_dir != HISTORY_DIR:
            for candidate in HISTORY_DIR.glob(f"{job_id}.*"):
                if candidate.suffix.lower() != ".json":
                    return candidate

        return None

    @staticmethod
    def delete(job_id: str, session_id: Optional[str] = None) -> bool:
        """Exclui a transcrição e qualquer arquivo de áudio associado dentro do escopo da sessão."""
        target_dir = get_session_dir(session_id)
        success = False
        for p in target_dir.glob(f"{job_id}.*"):
            try:
                os.remove(p)
                success = True
            except Exception:
                pass

        if not success and not settings.is_public and target_dir != HISTORY_DIR:
            for p in HISTORY_DIR.glob(f"{job_id}.*"):
                try:
                    os.remove(p)
                    success = True
                except Exception:
                    pass

        return success
