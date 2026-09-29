import sys
import time
import argparse
import random
import webbrowser
import threading
import uvicorn

# Corrige aviso nativo do asyncio no Windows (WinError 10054) quando o navegador encerra streaming de áudio
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
        def _silent_call_connection_lost(self, exc=None):
            try:
                _orig_call_connection_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass
        _ProactorBasePipeTransport._call_connection_lost = _silent_call_connection_lost
    except Exception:
        pass

from app.core.config import settings
from app.services.tunnel import TunnelService

def parse_args():
    parser = argparse.ArgumentParser(description="Transcribe Studio - Servidor de Transcrição")
    parser.add_argument("--port", type=int, default=settings.port, help="Porta do servidor (padrão: 8000)")
    parser.add_argument("--host", type=str, default=settings.host, help="Host do servidor (padrão: 0.0.0.0)")
    parser.add_argument("--mode", type=str, choices=["private", "public", "byok"], default=None, help="Modo da instância (private, public, byok)")
    parser.add_argument("--pin", type=str, default=None, help="PIN de acesso de segurança para modo privado")
    parser.add_argument("--public", action="store_true", help="Inicia como instância pública (sem túnel obrigatório)")
    parser.add_argument("--share", action="store_true", help="Inicia túnel seguro Cloudflare para acesso remoto / celular")
    parser.add_argument("--tunnel", action="store_true", help="Inicia túnel Cloudflare opcional")
    parser.add_argument("--no-browser", action="store_true", help="Não abre o navegador automaticamente")
    return parser.parse_args()

def open_browser(url: str):
    time.sleep(1.8)
    webbrowser.open(url)

if __name__ == "__main__":
    args = parse_args()

    # Aplica argumentos na configuração
    settings.port = args.port
    settings.host = args.host

    if args.public:
        settings.set_mode("public")
    elif args.mode:
        settings.set_mode(args.mode)

    if args.share or args.tunnel:
        settings.enable_tunnel = True

    if args.pin:
        settings.access_pin = args.pin.strip()
    elif settings.is_private and settings.enable_tunnel and not settings.access_pin:
        # Gera PIN aleatório seguro de 6 dígitos se for compartilhar sem senha prévia
        settings.access_pin = str(random.randint(100000, 999999))

    # Inicia túnel se solicitado
    tunnel_thread = None
    if settings.enable_tunnel:
        def _tunnel_worker():
            try:
                # Aguarda servidor iniciar brevemente antes de abrir túnel
                time.sleep(1.0)
                url = TunnelService.start_tunnel(port=settings.port)
                if url:
                    TunnelService.print_banner(port=settings.port)
            except Exception as e:
                print(f"[Tunnel] Erro ao iniciar túnel: {e}")

        tunnel_thread = threading.Thread(target=_tunnel_worker, daemon=True)
        tunnel_thread.start()

    # Banner inicial local
    TunnelService.print_banner(port=settings.port)

    # Abre navegador se não desabilitado
    if not args.no_browser:
        target_local_url = f"http://localhost:{settings.port}"
        if settings.is_private and settings.access_pin:
            target_local_url += f"?pin={settings.access_pin}"
        threading.Thread(target=open_browser, args=(target_local_url,), daemon=True).start()

    # Inicia servidor ASGI
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
