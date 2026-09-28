import os
import sys
import time
import subprocess
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

def seed_demo_history():
    history_dir = BASE_DIR / "exports" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    demo_file = history_dir / "demo_transcription.json"
    data = {
        "id": "demo_transcription",
        "filename": "podcast_ia_futuro.mp3",
        "saved_at": "28/09/2026 17:15",
        "timestamp": 1727554500.0,
        "duration": 48.5,
        "language": "pt",
        "provider": "faster-whisper",
        "model": "faster-whisper-base",
        "text": "Sejam todos muito bem-vindos a mais um episódio do nosso podcast sobre tecnologia e inteligência artificial. Hoje vamos discutir o avanço dos modelos de reconhecimento de fala com faster-whisper e a computação local sem dependência de nuvem.",
        "segments": [
            {
                "id": 1,
                "start": 0.0,
                "end": 6.2,
                "text": "Sejam todos muito bem-vindos a mais um episódio do nosso podcast sobre tecnologia e inteligência artificial."
            },
            {
                "id": 2,
                "start": 6.5,
                "end": 14.8,
                "text": "Hoje vamos discutir o avanço dos modelos de reconhecimento de fala com faster-whisper e a computação local sem dependência de nuvem."
            },
            {
                "id": 3,
                "start": 15.2,
                "end": 22.0,
                "text": "Com a quantização em int8, é possível rodar modelos modernos diretamente na CPU com alta eficiência e baixo consumo de memória."
            },
            {
                "id": 4,
                "start": 22.5,
                "end": 31.0,
                "text": "Além disso, a integração com whisper.cpp e APIs na nuvem como Groq trazem flexibilidade para qualquer cenário de uso."
            }
        ],
        "exports": {
            "txt": "Sejam todos muito bem-vindos...",
            "srt": "1\n00:00:00,000 --> 00:00:06,200\nSejam todos muito bem-vindos...",
            "vtt": "WEBVTT\n\n00:00:00.000 --> 00:00:06.200\nSejam todos muito bem-vindos...",
            "json": "{}"
        }
    }
    with open(demo_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return demo_file

def main():
    print("[1/4] Criando exemplo de transcrição para demonstração...")
    seed_demo_history()

    print("[2/4] Iniciando servidor temporário FastAPI...")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8008"],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2.5) # Aguarda inicialização

    try:
        preview_png = SCREENSHOTS_DIR / "preview.png"
        transcription_png = SCREENSHOTS_DIR / "transcription_view.png"
        
        print(f"[3/4] Capturando preview em {preview_png} (1440x1180) ...")
        edge_cmd1 = [
            EDGE_PATH,
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            "--window-size=1440,1180",
            f"--screenshot={str(preview_png)}",
            "http://127.0.0.1:8008"
        ]
        subprocess.run(edge_cmd1, check=True)
        print(" -> preview.png capturado!")

        print(f"[3.5/4] Capturando visualização de transcrição ativa em {transcription_png} (1440x1180) ...")
        edge_cmd2 = [
            EDGE_PATH,
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            "--window-size=1440,1180",
            f"--screenshot={str(transcription_png)}",
            "http://127.0.0.1:8008/?demo=1"
        ]
        subprocess.run(edge_cmd2, check=True)
        print(" -> transcription_view.png capturado!")


    finally:
        print("[4/4] Encerrando servidor temporário...")
        server_proc.terminate()
        server_proc.wait()

    print("\n[SUCESSO] Screenshots geradas com sucesso no Microsoft Edge!")

if __name__ == "__main__":
    main()
