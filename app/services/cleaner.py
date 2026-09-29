import os
import time
import shutil
import threading
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import UPLOAD_DIR, HISTORY_DIR, settings

class CleanerService:
    """Serviço de limpeza periódica de uploads temporários e históricos efêmeros."""

    _thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = threading.Event()

    @staticmethod
    def clean_uploads(max_age_minutes: int = 15) -> int:
        """Remove arquivos temporários esquecidos na pasta de uploads."""
        now = time.time()
        max_age_seconds = max_age_minutes * 60
        removed = 0

        if not UPLOAD_DIR.exists():
            return 0

        for file_path in UPLOAD_DIR.glob("*"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue
            try:
                mtime = file_path.stat().st_mtime
                if (now - mtime) > max_age_seconds:
                    file_path.unlink()
                    removed += 1
            except Exception as e:
                print(f"[Cleaner] Aviso ao remover upload temporário {file_path.name}: {e}")

        return removed

    @staticmethod
    def clean_expired_history(max_age_minutes: Optional[int] = None) -> int:
        """
        Histórico e áudios são persistentes permanentemente no disco.
        A expiração automática foi desativada. Limpeza de histórico ocorre apenas se
        um valor de max_age_minutes > 0 for explicitamente fornecido.
        """
        expire_mins = max_age_minutes if max_age_minutes is not None else settings.cleanup_expire_minutes
        if not expire_mins or expire_mins <= 0:
            return 0

        max_age_seconds = expire_mins * 60
        now = time.time()
        removed = 0

        if not HISTORY_DIR.exists():
            return 0

        # Limpa subpastas de sessões se explicitamente requisitado via max_age_minutes
        for session_dir in HISTORY_DIR.iterdir():
            if not session_dir.is_dir():
                continue

            session_files_removed = 0
            session_files_total = 0

            for file_path in session_dir.glob("*"):
                session_files_total += 1
                try:
                    mtime = file_path.stat().st_mtime
                    if (now - mtime) > max_age_seconds:
                        file_path.unlink()
                        session_files_removed += 1
                        removed += 1
                except Exception as e:
                    print(f"[Cleaner] Falha ao remover arquivo de sessão {file_path.name}: {e}")

            # Se a pasta de sessão ficou vazia, remove o diretório da sessão
            try:
                remaining = list(session_dir.iterdir())
                if len(remaining) == 0:
                    session_dir.rmdir()
            except Exception:
                pass

        return removed

    @classmethod
    def clean_all(cls) -> Dict[str, int]:
        """Executa varredura de limpeza de uploads temporários (preserva histórico permanentemente)."""
        uploads_removed = cls.clean_uploads()
        history_removed = cls.clean_expired_history()
        return {
            "uploads_removed": uploads_removed,
            "history_removed": history_removed,
            "total_removed": uploads_removed + history_removed
        }

    @classmethod
    def _run_loop(cls):
        """Loop contínuo em segundo plano para limpeza de uploads temporários."""
        print(f"[Cleaner] Auto-Cleaner iniciado (limpeza de uploads a cada {settings.cleanup_interval_seconds}s; histórico permanente ativo).")
        while not cls._stop_event.is_set():
            try:
                stats = cls.clean_all()
                if stats["uploads_removed"] > 0:
                    print(f"[Cleaner] Varredura periódica: {stats['uploads_removed']} uploads temporários esquecidos removidos.")
            except Exception as e:
                print(f"[Cleaner] Erro no ciclo de limpeza: {e}")

            # Aguarda o intervalo ou sinal de encerramento
            cls._stop_event.wait(timeout=settings.cleanup_interval_seconds)

    @classmethod
    def start(cls):
        """Inicia o serviço em segundo plano (idempotente)."""
        if cls._thread and cls._thread.is_alive():
            return
        cls._stop_event.clear()
        cls._thread = threading.Thread(target=cls._run_loop, daemon=True, name="TranscribeAutoCleaner")
        cls._thread.start()

    @classmethod
    def stop(cls):
        """Encerra o serviço graciosamente."""
        if cls._thread and cls._thread.is_alive():
            cls._stop_event.set()
            cls._thread.join(timeout=2.0)
            cls._thread = None
