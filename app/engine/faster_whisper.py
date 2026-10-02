import time
import os
from typing import Optional, Callable, Dict
import av

# Wrapper defensivo em av.open para blindar contra ambientes com PyAV legado
# onde 'metadata_errors' nao e suportado como argumento.
if not getattr(av, "_is_safe_patched", False):
    _orig_av_open = av.open

    def _safe_av_open(*args, **kwargs):
        try:
            return _orig_av_open(*args, **kwargs)
        except TypeError:
            if "metadata_errors" in kwargs:
                clean_kwargs = dict(kwargs)
                clean_kwargs.pop("metadata_errors", None)
                return _orig_av_open(*args, **clean_kwargs)
            raise

    av.open = _safe_av_open
    av._is_safe_patched = True

from faster_whisper import WhisperModel
import ctranslate2

from app.engine.base import BaseTranscriber, TranscriptionResult, TranscriptionSegment

# Cache global de modelos para evitar recarregar pesos na RAM repetidamente
_MODEL_CACHE: Dict[str, WhisperModel] = {}

def get_audio_duration(file_path: str) -> float:
    """Obtém a duração do áudio em segundos usando PyAV sem depender do ffmpeg.exe externo."""
    try:
        with av.open(file_path) as container:
            if container.duration is not None:
                return float(container.duration) / float(av.time_base)
            # Tentar pelo stream de áudio
            for stream in container.streams.audio:
                if stream.duration is not None and stream.time_base is not None:
                    return float(stream.duration * stream.time_base)
    except Exception:
        pass
    return 0.0

class FasterWhisperTranscriber(BaseTranscriber):
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.cuda_available = ctranslate2.get_cuda_device_count() > 0
        self.device = "cuda" if self.cuda_available else "cpu"
        self.compute_type = "float16" if self.cuda_available else "int8"

    def _get_model(self) -> WhisperModel:
        cache_key = f"{self.model_size}_{self.device}_{self.compute_type}"
        if cache_key not in _MODEL_CACHE:
            _MODEL_CACHE[cache_key] = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
        return _MODEL_CACHE[cache_key]

    def transcribe(
        self,
        file_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        **kwargs
    ) -> TranscriptionResult:
        if progress_callback:
            progress_callback(5.0, f"Carregando modelo faster-whisper ({self.model_size})...")

        model = self._get_model()
        total_duration = get_audio_duration(file_path)

        if progress_callback:
            progress_callback(15.0, "Iniciando processamento do áudio...")

        # faster-whisper aceita diretamente o caminho do arquivo
        # e decodifica internamente com PyAV
        lang_arg = language if (language and language.strip() and language.strip().lower() != "auto") else None
        prompt_arg = (prompt.strip()[:500]) if (prompt and prompt.strip()) else None

        segments_generator, info = model.transcribe(
            file_path,
            language=lang_arg,
            task=task,
            initial_prompt=prompt_arg,
            beam_size=kwargs.get("beam_size", 5),
            word_timestamps=kwargs.get("word_timestamps", True)
        )

        detected_language = info.language
        audio_duration = info.duration if info.duration > 0 else total_duration

        segments_list = []
        full_text_parts = []
        seg_idx = 1

        for seg in segments_generator:
            words_list = None
            if hasattr(seg, "words") and seg.words:
                words_list = [
                    {
                        "word": w.word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 2) if hasattr(w, "probability") and w.probability is not None else 1.0
                    }
                    for w in seg.words
                ]
            segment_item = TranscriptionSegment(
                id=seg_idx,
                start=round(seg.start, 2),
                end=round(seg.end, 2),
                text=seg.text.strip(),
                words=words_list
            )
            segments_list.append(segment_item)
            full_text_parts.append(seg.text.strip())

            # Cálculo de progresso percentual baseado no timestamp final do segmento
            if progress_callback and audio_duration > 0:
                # 20% a 95% reservado para a transcrição dos trechos
                pct = min(95.0, 20.0 + (seg.end / audio_duration) * 75.0)
                progress_callback(round(pct, 1), f"Transcrevendo: {seg.end:.1f}s / {audio_duration:.1f}s")

            seg_idx += 1

        if progress_callback:
            progress_callback(100.0, "Transcrição concluída com sucesso!")

        return TranscriptionResult(
            text=" ".join(full_text_parts),
            segments=segments_list,
            language=detected_language,
            duration=round(audio_duration, 2),
            model=f"faster-whisper-{self.model_size}",
            provider="faster-whisper"
        )
