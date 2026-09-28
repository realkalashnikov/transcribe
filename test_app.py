import os
import wave
import struct
import math
from pathlib import Path
from app.engine.faster_whisper import FasterWhisperTranscriber, get_audio_duration
from app.services.exporter import Exporter
from app.engine.base import TranscriptionResult, TranscriptionSegment

def generate_test_wav(filename="test_sample.wav", duration=2.0, freq=440.0):
    """Gera um arquivo WAV de teste simples de 2 segundos com onda senoidal."""
    sample_rate = 16000
    n_samples = int(sample_rate * duration)
    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1) # mono
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            data = struct.pack("<h", value)
            wav_file.writeframes(data)
    return filename

def test_transcriber_and_exporter():
    print("[1/3] Gerando áudio de teste WAV...")
    test_file = generate_test_wav()
    assert os.path.exists(test_file)
    print(f" -> Arquivo criado: {test_file}")

    print("[2/3] Testando PyAV duration e motor FasterWhisper...")
    duration = get_audio_duration(test_file)
    print(f" -> Duração detectada via PyAV: {duration:.2f}s")
    assert duration > 1.5, f"Duração inesperada: {duration}"

    # Testando FasterWhisper com modelo tiny para ser ultrarrápido
    transcriber = FasterWhisperTranscriber(model_size="tiny")
    
    def on_progress(pct, msg):
        print(f"   [Progresso] {pct:.1f}% - {msg}")

    result = transcriber.transcribe(test_file, progress_callback=on_progress)
    print(" -> Transcrição local (faster-whisper) executada com sucesso!")
    print(f" -> Idioma detectado: {result.language}, Duração: {result.duration}s")

    print("[2.5/3] Testando importação e motor WhisperCppTranscriber...")
    from app.engine.whisper_cpp import WhisperCppTranscriber
    cpp_transcriber = WhisperCppTranscriber(model_size="tiny")
    print(" -> WhisperCppTranscriber instanciado com sucesso!")

    print("[3/3] Testando Exportações (TXT, SRT, VTT, JSON)...")
    # Simula segmentos caso o tom senoidal não tenha fala
    if not result.segments:
        result.segments = [
            TranscriptionSegment(id=1, start=0.0, end=1.0, text="Olá mundo"),
            TranscriptionSegment(id=2, start=1.0, end=2.0, text="Teste de transcrição")
        ]
        result.text = "Olá mundo Teste de transcrição"

    txt = Exporter.to_txt(result)
    srt = Exporter.to_srt(result)
    vtt = Exporter.to_vtt(result)
    json_str = Exporter.to_json(result)

    assert "Olá mundo" in txt
    assert "-->" in srt
    assert "WEBVTT" in vtt
    assert '"language":' in json_str

    print(" -> Exportações validadas com sucesso!")

    # Limpeza
    if os.path.exists(test_file):
        os.remove(test_file)

    print("\n[SUCESSO] TODOS OS TESTES PASSARAM COM SUCESSO!")

if __name__ == "__main__":
    test_transcriber_and_exporter()
