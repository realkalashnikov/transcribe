import os
import sys
import time
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

def capture_edge(url: str, output_path: Path, width: int, height: int, scale: float, profile_dir: str):
    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-scrollbars",
        f"--user-data-dir={profile_dir}",
        "--disk-cache-size=0",
        f"--window-size={width},{height}",
        f"--force-device-scale-factor={scale}",
        f"--screenshot={str(output_path)}",
        url
    ]
    subprocess.run(cmd, check=True)

def seed_demo_history():
    import wave
    import struct
    import math

    history_dir = BASE_DIR / "exports" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    demo_file = history_dir / "demo_transcription.json"
    wav_file = history_dir / "demo_transcription.wav"

    sample_rate = 16000
    n_samples = int(sample_rate * 2.0)
    with wave.open(str(wav_file), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            val = int(32767.0 * 0.1 * math.sin(2.0 * math.pi * 440.0 * (i / sample_rate)))
            wf.writeframes(struct.pack("<h", val))

    data = {
        "id": "demo_transcription",
        "filename": "podcast_ia_futuro.mp3",
        "audio_file": "demo_transcription.wav",
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
                "text": "Sejam todos muito bem-vindos a mais um episódio do nosso podcast sobre tecnologia e inteligência artificial.",
                "words": [
                    {"word": "Sejam", "start": 0.0, "end": 0.4},
                    {"word": "todos", "start": 0.45, "end": 0.8},
                    {"word": "muito", "start": 0.85, "end": 1.2},
                    {"word": "bem-vindos", "start": 1.25, "end": 1.8},
                    {"word": "a", "start": 1.85, "end": 2.0},
                    {"word": "mais", "start": 2.05, "end": 2.3},
                    {"word": "um", "start": 2.35, "end": 2.5},
                    {"word": "episódio", "start": 2.55, "end": 3.1},
                    {"word": "do", "start": 3.15, "end": 3.3},
                    {"word": "nosso", "start": 3.35, "end": 3.6},
                    {"word": "podcast", "start": 3.65, "end": 4.2},
                    {"word": "sobre", "start": 4.25, "end": 4.6},
                    {"word": "tecnologia", "start": 4.65, "end": 5.3},
                    {"word": "e", "start": 5.35, "end": 5.5},
                    {"word": "inteligência", "start": 5.55, "end": 6.0},
                    {"word": "artificial.", "start": 6.05, "end": 6.2}
                ]
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

    temp_profile = tempfile.mkdtemp(prefix="edge_profile_")

    try:
        preview_png = SCREENSHOTS_DIR / "preview.png"
        transcription_png = SCREENSHOTS_DIR / "transcription_view.png"
        remote_png = SCREENSHOTS_DIR / "remote_modal.png"
        story_png = SCREENSHOTS_DIR / "story_status.png"
        cli_png = SCREENSHOTS_DIR / "cli_menu.png"
        
        # 1. 16:9 Feed Format - Preview limpo da UI completa
        print(f"[3/7] Capturando preview em {preview_png} (Feed 1600x1300)...")
        capture_edge("http://127.0.0.1:8008", preview_png, 1600, 1300, 1.15, temp_profile)
        print(" -> preview.png capturado!")

        # 1.5 Aba de Ingestão por Link da Web
        url_png = SCREENSHOTS_DIR / "url_ingestion.png"
        print(f"[*] Capturando aba de ingestão por URL em {url_png}...")
        capture_edge("http://127.0.0.1:8008/?tab=url", url_png, 1600, 1200, 1.15, temp_profile)
        print(" -> url_ingestion.png capturado!")

        # 2. Feed Format com Transcrição ativa e Player de Áudio
        print(f"[4/7] Capturando transcrição ativa em {transcription_png} (Feed 1600x1200)...")
        capture_edge("http://127.0.0.1:8008/?demo=1", transcription_png, 1600, 1200, 1.15, temp_profile)
        print(" -> transcription_view.png capturado!")

        # 3. Feed Format com Modal de Acesso Remoto & QR Code Interativo
        print(f"[5/7] Capturando modal de acesso remoto em {remote_png} (Feed 1600x1200)...")
        capture_edge("http://127.0.0.1:8008/?demo=1&remote=1", remote_png, 1600, 1200, 1.15, temp_profile)
        print(" -> remote_modal.png capturado!")

        # ========================================================
        # PRINTS DEDICADOS DE ALTA DEFINIÇÃO PARA O LINKEDIN
        # ========================================================
        linkedin_dir = SCREENSHOTS_DIR / "linkedin"
        linkedin_dir.mkdir(parents=True, exist_ok=True)
        print("\n[+] Gerando pacote de prints em alta resolução dedicados para o LinkedIn...")

        # LinkedIn 1: Seleção de Motores & Modelos (Local vs Nuvem)
        print(" -> Gerando 1_motores_e_modelos.png...")
        capture_edge("http://127.0.0.1:8008/?focus=motores", linkedin_dir / "1_motores_e_modelos.png", 1000, 1050, 1.6, temp_profile)

        # LinkedIn 2: Ingestão por Link da Web / YouTube + Fila Ativa
        print(" -> Gerando 2_transcricao_por_url.png...")
        capture_edge("http://127.0.0.1:8008/?focus=url", linkedin_dir / "2_transcricao_por_url.png", 1150, 900, 1.6, temp_profile)

        # LinkedIn 3: Player Integrado, Timestamps Clicáveis e Edição Inline
        print(" -> Gerando 3_player_e_minutagem.png...")
        capture_edge("http://127.0.0.1:8008/?focus=player&demo=1", linkedin_dir / "3_player_e_minutagem.png", 1100, 1100, 1.55, temp_profile)

        # LinkedIn 4: Ações com IA (Resumo Executivo, Ata de Reunião com Llama/Gemini)
        print(" -> Gerando 4_acoes_ia_resumo.png...")
        capture_edge("http://127.0.0.1:8008/?focus=ai&demo=1", linkedin_dir / "4_acoes_ia_resumo.png", 1100, 950, 1.55, temp_profile)

        # LinkedIn 5: Visão Geral em Alta Resolução
        print(" -> Gerando 5_visao_geral.png...")
        capture_edge("http://127.0.0.1:8008/?demo=1", linkedin_dir / "5_visao_geral.png", 1500, 1100, 1.35, temp_profile)

        # 4. 9:16 Vertical Format para WhatsApp Status, Instagram Stories e Facebook Stories
        print(f"[6/7] Capturando formato vertical Story/Status em {story_png} (9:16 vertical)...")
        capture_edge("http://127.0.0.1:8008/?demo=1&story=1", story_png, 720, 1280, 1.5, temp_profile)
        print(" -> story_status.png capturado com sucesso!")

        # 5. Captura da Janela do Menu CLI Interativo
        print(f"[7/7] Gerando visual da CLI Interativa em {cli_png}...")
        cli_html = BASE_DIR / "scripts" / "_cli_mockup.html"
        cli_html.write_text("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    margin: 0;
    padding: 40px;
    background: #090d16;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
    box-sizing: border-box;
  }
  .terminal-window {
    width: 900px;
    background: #0d121f;
    border: 1px solid #1f293d;
    border-radius: 12px;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6), 0 0 30px rgba(99, 102, 241, 0.15);
    overflow: hidden;
  }
  .title-bar {
    background: #111827;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid #1f293d;
  }
  .buttons {
    display: flex;
    gap: 8px;
  }
  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }
  .dot-red { background: #ef4444; }
  .dot-yellow { background: #f59e0b; }
  .dot-green { background: #10b981; }
  .title {
    flex: 1;
    text-align: center;
    font-size: 13px;
    color: #94a3b8;
    margin-right: 50px;
    font-weight: 500;
  }
  .terminal-body {
    padding: 32px 36px 40px;
    font-size: 16px;
    line-height: 1.8;
  }
  .header {
    color: #06b6d4;
    font-weight: bold;
    text-decoration: underline;
    font-size: 18px;
    margin-bottom: 24px;
    display: inline-block;
  }
  .menu-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 28px;
  }
  .menu-item {
    padding: 8px 16px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    color: #cbd5e1;
    transition: all 0.15s ease;
  }
  .menu-item.active {
    background: #1e3a8a;
    color: #4ade80;
    font-weight: bold;
    box-shadow: 0 4px 12px rgba(30, 58, 138, 0.4);
  }
  .menu-item .icon {
    margin-right: 12px;
    font-size: 15px;
  }
  .menu-item.active .icon {
    color: #4ade80;
  }
  .menu-item .exit-icon {
    color: #ef4444;
  }
  .menu-item.exit {
    color: #f87171;
  }
  .hint {
    color: #64748b;
    font-size: 13px;
    margin-top: 10px;
    border-top: 1px dashed #1f293d;
    padding-top: 16px;
  }
</style>
</head>
<body>
  <div class="terminal-window">
    <div class="title-bar">
      <div class="buttons">
        <div class="dot dot-red"></div>
        <div class="dot dot-yellow"></div>
        <div class="dot dot-green"></div>
      </div>
      <div class="title">Transcribe Studio — Terminal CLI</div>
    </div>
    <div class="terminal-body">
      <div class="header">🗂 Transcribe Studio — Menu Principal</div>
      <div class="menu-list">
        <div class="menu-item active">
          <span class="icon">◈</span>
          <span>1. Modo Local Pessoal (Apenas neste computador - Padrão)</span>
        </div>
        <div class="menu-item">
          <span class="icon">◈</span>
          <span>2. Instância Pública / Amigos (Rede ou VPS com domínio)</span>
        </div>
        <div class="menu-item">
          <span class="icon">◈</span>
          <span>3. Túnel Cloudflare (Acesso externo rápido sem IP fixo / Celular)</span>
        </div>
        <div class="menu-item exit">
          <span class="icon exit-icon">✕</span>
          <span>4. Sair</span>
        </div>
      </div>
      <div class="hint">
        (Use as setas ↑/↓ para navegar, Enter para confirmar ou 1-4 para atalho)
      </div>
    </div>
  </div>
</body>
</html>""", encoding="utf-8")
        
        capture_edge(f"file:///{str(cli_html).replace('\\\\', '/')}", cli_png, 1060, 560, 1.2, temp_profile)
        try:
            cli_html.unlink()
        except Exception:
            pass
        print(" -> cli_menu.png capturado com sucesso!")


    finally:
        print("[4/4] Encerrando servidor temporário...")
        server_proc.terminate()
        server_proc.wait()
        try:
            shutil.rmtree(temp_profile, ignore_errors=True)
        except Exception:
            pass

    print("\n[SUCESSO] Screenshots geradas com sucesso no Microsoft Edge!")

if __name__ == "__main__":
    main()
