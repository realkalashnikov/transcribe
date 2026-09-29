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

def sanitize_job_id(job_id: Optional[str]) -> Optional[str]:
    """Valida e sanitiza o job_id para prevenir directory traversal e glob injection."""
    if not job_id:
        return None
    job_clean = str(job_id).strip()
    if re.match(r"^[a-zA-Z0-9_-]{1,64}$", job_clean):
        return job_clean
    return None

def get_session_dir(session_id: Optional[str] = None) -> Path:
    """
    Retorna o diretório de histórico correspondente (Opção A - Zero Burocracia):
    - Cada navegador/dispositivo recebe sua própria pasta isolada e permanente (HISTORY_DIR / safe_session).
    - Se nenhum session_id for informado, utiliza a pasta padrão raiz HISTORY_DIR.
    """
    safe_session = sanitize_session_id(session_id)
    if safe_session:
        target_dir = HISTORY_DIR / safe_session
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
        safe_job = sanitize_job_id(job_id)
        if not safe_job:
            raise ValueError(f"Job ID inválido: {job_id}")

        target_dir = get_session_dir(session_id)
        audio_saved_name = None

        if audio_path and os.path.exists(audio_path):
            ext = os.path.splitext(audio_path)[1].lower() or ".mp3"
            dest_audio = target_dir / f"{safe_job}{ext}"
            try:
                shutil.copy2(audio_path, dest_audio)
                audio_saved_name = f"{safe_job}{ext}"
            except Exception as e:
                print(f"[Aviso] Falha ao salvar áudio no histórico: {e}")

        file_path = target_dir / f"{safe_job}.json"
        data = {
            "id": safe_job,
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

        # Se existir demo_transcription na raiz, inclui como item de demonstração
        root_demo = HISTORY_DIR / "demo_transcription.json"
        if root_demo.exists() and not any(it["id"] == "demo_transcription" for it in items):
            try:
                with open(root_demo, "r", encoding="utf-8") as f:
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
                pass

        # Ordena pelo timestamp decrescente
        items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return items

    @staticmethod
    def get(job_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Obtém os dados completos de uma transcrição salva no escopo da sessão."""
        safe_job = sanitize_job_id(job_id)
        if not safe_job:
            return None

        target_dir = get_session_dir(session_id)
        file_path = target_dir / f"{safe_job}.json"

        if not file_path.exists():
            if safe_job == "demo_transcription":
                root_fallback = HISTORY_DIR / f"{safe_job}.json"
                if root_fallback.exists():
                    file_path = root_fallback
                else:
                    return None
            else:
                return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def get_audio_path(job_id: str, session_id: Optional[str] = None) -> Optional[Path]:
        """Localiza o arquivo de áudio associado ao job_id no escopo da sessão."""
        safe_job = sanitize_job_id(job_id)
        if not safe_job:
            return None

        target_dir = get_session_dir(session_id)
        item = HistoryService.get(safe_job, session_id=session_id)
        if item and item.get("audio_file"):
            # Garante que o nome do arquivo de áudio não tenta escapar a pasta
            safe_audio_name = Path(item["audio_file"]).name
            p = target_dir / safe_audio_name
            if p.exists():
                return p

        # Busca por extensão dentro do target_dir com safe_job estrito (sem wildcard injection)
        for candidate in target_dir.glob(f"{safe_job}.*"):
            if candidate.suffix.lower() != ".json":
                return candidate

        return None

    @staticmethod
    def delete(job_id: str, session_id: Optional[str] = None) -> bool:
        """Exclui a transcrição e qualquer arquivo de áudio associado dentro do escopo da sessão."""
        safe_job = sanitize_job_id(job_id)
        if not safe_job:
            return False

        target_dir = get_session_dir(session_id)
        success = False
        for p in target_dir.glob(f"{safe_job}.*"):
            try:
                os.remove(p)
                success = True
            except Exception:
                pass

        return success
