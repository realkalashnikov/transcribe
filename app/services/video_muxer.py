import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

def get_ffmpeg_binary() -> Optional[str]:
    """Retorna o caminho do binário ffmpeg via imageio_ffmpeg ou PATH do sistema."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass

    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    return None

class VideoMuxer:
    @staticmethod
    def is_available() -> bool:
        return get_ffmpeg_binary() is not None

    @classmethod
    def mux_subtitles(
        cls,
        video_path: str,
        srt_content: str,
        output_path: Optional[str] = None,
        language: str = "por"
    ) -> str:
        """
        Embutir legenda SRT em contêiner MP4 como stream de texto 'mov_text'
        sem re-codificar áudio/vídeo (cópia direta em ~2 segundos).
        """
        ffmpeg_bin = get_ffmpeg_binary()
        if not ffmpeg_bin:
            raise RuntimeError("Binário do FFmpeg não encontrado para embutir legendas.")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Arquivo de mídia não encontrado: {video_path}")

        # Salva o SRT em arquivo temporário
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as srt_file:
            srt_file.write(srt_content)
            temp_srt_path = srt_file.name

        if not output_path:
            out_fd, output_path = tempfile.mkstemp(suffix=".mp4")
            os.close(out_fd)

        try:
            # Comando FFmpeg com -c copy para mux instantâneo
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", video_path,
                "-i", temp_srt_path,
                "-c:v", "copy",
                "-c:a", "copy",
                "-c:s", "mov_text",
                f"-metadata:s:s:0", f"language={language}",
                output_path
            ]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )

            if process.returncode != 0:
                # Se falhou com -c:v copy (ex: contêiner de entrada incompatível), tenta fallback convertendo para mp4
                cmd_fallback = [
                    ffmpeg_bin,
                    "-y",
                    "-i", video_path,
                    "-i", temp_srt_path,
                    "-c:s", "mov_text",
                    output_path
                ]
                process_fb = subprocess.run(
                    cmd_fallback,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                if process_fb.returncode != 0:
                    raise RuntimeError(f"Erro no FFmpeg: {process.stderr[:300]}")

            return output_path
        finally:
            try:
                if os.path.exists(temp_srt_path):
                    os.remove(temp_srt_path)
            except Exception:
                pass
