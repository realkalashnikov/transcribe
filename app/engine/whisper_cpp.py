import os
import wave
from typing import Optional, Callable, Dict
import numpy as np
import av
from pywhispercpp.model import Model

from app.engine.base import BaseTranscriber, TranscriptionResult, TranscriptionSegment
from app.engine.faster_whisper import get_audio_duration

_CPP_MODEL_CACHE: Dict[str, Model] = {}

def convert_to_wav16k(input_path: str, output_wav_path: str) -> None:
    """Converte qualquer arquivo de áudio ou vídeo para WAV 16kHz mono usando PyAV."""
    with av.open(input_path) as input_container:
        in_stream = input_container.streams.audio[0]
        resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=16000
        )
        with av.open(output_wav_path, mode="w", format="wav") as out_container:
            out_stream = out_container.add_stream("pcm_s16le", rate=16000)
            out_stream.layout = "mono"
            for packet in input_container.demux(in_stream):
                for frame in packet.decode():
                    frame.pts = None
                    for resampled in resampler.resample(frame):
                        for out_packet in out_stream.encode(resampled):
                            out_container.mux(out_packet)
            for out_packet in out_stream.encode(None):
                out_container.mux(out_packet)

class WhisperCppTranscriber(BaseTranscriber):
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size

    def _get_model(self) -> Model:
        # pywhispercpp aceita 'tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large-v3'
        clean_model = self.model_size.replace("-turbo", "")
        if clean_model not in _CPP_MODEL_CACHE:
            _CPP_MODEL_CACHE[clean_model] = Model(clean_model, n_threads=6)
        return _CPP_MODEL_CACHE[clean_model]

    def transcribe(
        self,
        file_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        **kwargs
    ) -> TranscriptionResult:
        if progress_callback:
            progress_callback(10.0, f"Carregando modelo whisper.cpp ({self.model_size})...")

        model = self._get_model()
        total_duration = get_audio_duration(file_path)

        if progress_callback:
            progress_callback(25.0, "Convertendo áudio para 16kHz mono...")

        # Converte para WAV temporário para o whisper.cpp processar
        temp_wav = file_path + ".temp16k.wav"
        try:
            convert_to_wav16k(file_path, temp_wav)
            target_file = temp_wav
        except Exception:
            target_file = file_path

        if progress_callback:
            progress_callback(40.0, "Transcrevendo via whisper.cpp (C++)...")

        lang = language if (language and language.strip() and language.strip().lower() != "auto") else None
        translate_flag = (task == "translate")

        try:
            # Transcreve com pywhispercpp
            segments_output = model.transcribe(
                target_file,
                language=lang,
                translate=translate_flag
            )

            segments_list = []
            full_text_parts = []
            seg_idx = 1

            for seg in segments_output:
                # seg tem start (ms), end (ms), text
                t0 = round(seg.t0 / 100.0, 2) if hasattr(seg, 't0') else 0.0
                t1 = round(seg.t1 / 100.0, 2) if hasattr(seg, 't1') else 0.0
                txt = seg.text.strip() if hasattr(seg, 'text') else str(seg).strip()

                segments_list.append(TranscriptionSegment(
                    id=seg_idx,
                    start=t0,
                    end=t1,
                    text=txt
                ))
                full_text_parts.append(txt)
                seg_idx += 1

            if progress_callback:
                progress_callback(100.0, "Transcrição com whisper.cpp finalizada!")

            return TranscriptionResult(
                text=" ".join(full_text_parts),
                segments=segments_list,
                language=language or "auto",
                duration=round(total_duration, 2),
                model=f"whisper.cpp-{self.model_size}",
                provider="whisper.cpp"
            )
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
