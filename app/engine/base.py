from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable

@dataclass
class TranscriptionSegment:
    id: int
    start: float
    end: float
    text: str
    words: Optional[List[Dict[str, Any]]] = None

@dataclass
class TranscriptionResult:
    text: str
    segments: List[TranscriptionSegment] = field(default_factory=list)
    language: str = "unknown"
    duration: float = 0.0
    model: str = ""
    provider: str = "faster-whisper"

class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(
        self,
        file_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcreve o arquivo de áudio/vídeo e retorna TranscriptionResult.
        """
        pass
