import sys
import time
import webbrowser
import threading
import uvicorn

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("=" * 60)
    print("  [Transcribe Studio] - faster-whisper & Cloud APIs")
    print("  Iniciando servidor local em http://localhost:8000 ...")
    print("=" * 60)

    # Abre o navegador automaticamente em uma thread separada
    threading.Thread(target=open_browser, daemon=True).start()

    # Inicia o servidor ASGI
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
