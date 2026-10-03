"""
Sistema de Bandeja (System Tray) para Transcribe Studio no Windows.
Exibe ícone discreto na barra de tarefas (perto do relógio) quando rodando em segundo plano,
permitindo abrir no navegador ou encerrar a aplicação com o botão direito.
"""

import os
import sys
import webbrowser
import threading
from typing import Optional, Callable
from PIL import Image, ImageDraw

_TRAY_ICON = None

def create_tray_image():
    """Gera um ícone nítido 64x64 em memória com as cores oficiais do Transcribe Studio."""
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Fundo roxo/índigo com cantos arredondados
    d.rounded_rectangle([(4, 4), (60, 60)], radius=14, fill=(99, 102, 241, 255))
    # Cápsula do microfone
    d.rounded_rectangle([(24, 14), (40, 36)], radius=8, fill=(255, 255, 255, 255))
    # Arco do suporte
    d.arc([(18, 22), (46, 44)], start=0, end=180, fill=(255, 255, 255, 255), width=3)
    # Haste e base
    d.line([(32, 44), (32, 50)], fill=(255, 255, 255, 255), width=3)
    d.line([(24, 50), (40, 50)], fill=(255, 255, 255, 255), width=3)
    return img

def start_tray_icon(port: int = 8000, access_pin: Optional[str] = None, on_exit: Optional[Callable] = None):
    """Inicia o ícone na bandeja do sistema em uma thread separada."""
    global _TRAY_ICON
    try:
        import pystray
    except ImportError:
        print("[Tray] pystray não disponível. Ícone de bandeja desabilitado.")
        return None

    target_url = f"http://localhost:{port}"
    if access_pin:
        target_url += f"?pin={access_pin}"

    def action_open_browser(icon, item):
        webbrowser.open(target_url)

    def action_exit(icon, item):
        try:
            icon.stop()
        except Exception:
            pass
        if on_exit:
            on_exit()
        else:
            os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Transcribe Studio (Ativo)", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Abrir no Navegador", action_open_browser, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Encerrar Servidor", action_exit)
    )

    image = create_tray_image()
    _TRAY_ICON = pystray.Icon("transcribe_studio", image, "Transcribe Studio", menu)

    def _run():
        try:
            _TRAY_ICON.run()
        except Exception as e:
            print(f"[Tray] Erro no loop de eventos da bandeja: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return _TRAY_ICON

def stop_tray_icon():
    """Para o ícone da bandeja se estiver ativo."""
    global _TRAY_ICON
    if _TRAY_ICON:
        try:
            _TRAY_ICON.stop()
        except Exception:
            pass
        _TRAY_ICON = None
