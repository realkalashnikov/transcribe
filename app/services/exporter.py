import json
from typing import List
from app.engine.base import TranscriptionResult, TranscriptionSegment

def format_timestamp_srt(seconds: float) -> str:
    """Converte segundos para formato SRT: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_timestamp_vtt(seconds: float) -> str:
    """Converte segundos para formato WebVTT: HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

class Exporter:
    @staticmethod
    def to_txt(result: TranscriptionResult) -> str:
        """Gera transcrição em texto puro."""
        return result.text.strip()

    @staticmethod
    def to_srt(result: TranscriptionResult) -> str:
        """Gera arquivo de legendas .SRT."""
        lines = []
        for i, seg in enumerate(result.segments, 1):
            start_str = format_timestamp_srt(seg.start)
            end_str = format_timestamp_srt(seg.end)
            lines.append(str(i))
            lines.append(f"{start_str} --> {end_str}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def to_vtt(result: TranscriptionResult) -> str:
        """Gera arquivo de legendas .VTT."""
        lines = ["WEBVTT", ""]
        for seg in result.segments:
            start_str = format_timestamp_vtt(seg.start)
            end_str = format_timestamp_vtt(seg.end)
            lines.append(f"{start_str} --> {end_str}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def to_json(result: TranscriptionResult) -> str:
        """Gera arquivo JSON estruturado com todos os metadados."""
        data = {
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "model": result.model,
            "provider": result.provider,
            "segments": [
                {
                    "id": seg.id,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text
                }
                for seg in result.segments
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
