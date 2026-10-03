import sys
import os
import time
import argparse
import random
import webbrowser
import threading
import subprocess
import signal
import uvicorn

# Tratamento para execução em background sem console (pythonw.exe)
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_bg.log")
if sys.stdout is None:
    try:
        sys.stdout = open(LOG_FILE, "a", encoding="utf-8")
    except Exception:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    try:
        sys.stderr = open(LOG_FILE, "a", encoding="utf-8")
    except Exception:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Configuração de encoding seguro do console
if sys.platform == "win32":
    try:
        os.system("")
    except Exception:
        pass
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.pid")


def write_pid():
    """Registra o PID do servidor atual para controle de parada."""
    try:
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def remove_pid():
    """Remove o arquivo de PID ao encerrar."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass


def find_pid_by_port(port: int):
    """Localiza o PID de qualquer processo escutando na porta especificada."""
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True,
            )
            for line in res.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    candidate = parts[-1]
                    if candidate.isdigit() and int(candidate) != os.getpid():
                        return int(candidate)
        except Exception:
            pass
    return None


def stop_background_server():
    """Encerra o servidor em segundo plano caso esteja ativo."""
    stopped = False
    pids_to_kill = set()

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid_str = f.read().strip()
            if pid_str.isdigit():
                pids_to_kill.add(int(pid_str))
        except Exception:
            pass
        finally:
            remove_pid()

    # Também localiza pelo número da porta configurada
    port_pid = find_pid_by_port(settings.port)
    if port_pid and port_pid != os.getpid():
        pids_to_kill.add(port_pid)

    for pid in pids_to_kill:
        try:
            if sys.platform == "win32":
                res = subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    stopped = True
            else:
                os.kill(pid, signal.SIGTERM)
                stopped = True
        except Exception as e:
            print(f"[Aviso] Falha ao encerrar processo PID {pid}: {e}")

    # No Windows, encerra também quaisquer processos pythonw rodando run.py se ainda houver
    if sys.platform == "win32":
        try:
            cmd = 'wmic process where "caption=\'pythonw.exe\' and commandline like \'%run.py%\'" call terminate'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if "ReturnValue = 0" in res.stdout:
                stopped = True
        except Exception:
            pass

    if stopped:
        print("\033[92m[OK] Servidor em segundo plano encerrado com sucesso.\033[0m")
    else:
        print("\033[93m[INFO] Nenhum servidor em segundo plano ativo encontrado.\033[0m")


def start_background_process(port: int, host: str, public: bool = False, tunnel: bool = False):
    """Inicia o servidor de forma totalmente invisível e em segundo plano."""
    # Encerra qualquer instância anterior antes de iniciar nova
    stop_background_server()

    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.py")
    cmd = [python_exe, script_path, "--tray", "--no-browser", "--port", str(port), "--host", host]
    if public:
        cmd.append("--public")
    if tunnel:
        cmd.append("--tunnel")

    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        # CREATE_NO_WINDOW (0x08000000) e CREATE_NEW_PROCESS_GROUP (0x00000200)
        creationflags = 0x08000000 | 0x00000200

    log_file_handle = open(LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=log_file_handle,
        stderr=subprocess.STDOUT,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )

    # Grava o PID do processo disparado
    try:
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(proc.pid))
    except Exception:
        pass

    print()
    print("\033[95m====================================================================\033[0m")
    print("\033[1;95m  [OK] Transcribe Studio iniciado em Segundo Plano!\033[0m")
    print("\033[95m====================================================================\033[0m")
    print(f"  * PID do Processo: {proc.pid}")
    print(f"  * Endereço: http://localhost:{port}")
    print("  * \033[1;96mBandeja do Windows (System Tray):\033[0m Veja o ícone perto do relógio!")
    print("    - Clique com o botão direito para \033[1m'Abrir no Navegador'\033[0m")
    print("    - Clique em \033[1;91m'Encerrar Servidor'\033[0m para fechar")
    print("  * \033[1;93mAtalho rápido:\033[0m Dê 2 cliques em \033[1mparar_servidor.bat\033[0m a qualquer momento.")
    print("\033[95m====================================================================\033[0m\n")


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
    parser.add_argument("--tray", action="store_true", help="Habilita ícone na bandeja do Windows (System Tray)")
    parser.add_argument("--background", action="store_true", help="Executa em segundo plano com ícone na bandeja")
    parser.add_argument("--stop", action="store_true", help="Para o servidor em segundo plano")
    parser.add_argument("--open", action="store_true", help="Abre o Transcribe Studio no navegador")
    return parser.parse_args()


def open_browser(url: str):
    time.sleep(1.8)
    webbrowser.open(url)


if __name__ == "__main__":
    args = parse_args()

    # Comandos diretos de controle
    if args.stop:
        stop_background_server()
        sys.exit(0)

    if args.open:
        target_local_url = f"http://localhost:{args.port}"
        print(f"Abrindo Transcribe Studio em {target_local_url}...")
        webbrowser.open(target_local_url)
        sys.exit(0)

    if args.background:
        start_background_process(args.port, args.host, args.public, args.tunnel or args.share)
        sys.exit(0)

    # Se executado sem flags em terminal interativo, aciona o Menu CLI Moderno
    if len(sys.argv) == 1 and sys.stdin.isatty():
        from app.core.cli_menu import run_interactive_menu
        choice = run_interactive_menu()
        if choice == "local_no_browser":
            args.no_browser = True
        elif choice == "background":
            start_background_process(args.port, args.host, False, False)
            sys.exit(0)
        elif choice == "public":
            args.public = True
        elif choice == "tunnel":
            args.tunnel = True
        elif choice == "open_browser":
            target_local_url = f"http://localhost:{args.port}"
            webbrowser.open(target_local_url)
            sys.exit(0)
        elif choice == "stop_background":
            stop_background_server()
            sys.exit(0)
        elif choice == "exit" or choice is None:
            sys.exit(0)

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

    # Grava o PID do servidor em execução
    write_pid()

    # Habilita ícone na bandeja se solicitado ou se estiver rodando com pythonw/background
    tray_icon = None
    if args.tray or sys.platform == "win32":
        try:
            from app.core.tray import start_tray_icon, stop_tray_icon
            def on_tray_exit():
                remove_pid()
                os._exit(0)
            tray_icon = start_tray_icon(
                port=settings.port,
                access_pin=settings.access_pin,
                on_exit=on_tray_exit,
            )
        except Exception as e:
            print(f"[Tray] Aviso: Não foi possível carregar ícone de bandeja: {e}")

    # Banner inicial local
    TunnelService.print_banner(port=settings.port)

    # Abre navegador se não desabilitado
    if not args.no_browser:
        target_local_url = f"http://localhost:{settings.port}"
        if settings.is_private and settings.access_pin:
            target_local_url += f"?pin={settings.access_pin}"
        threading.Thread(target=open_browser, args=(target_local_url,), daemon=True).start()

    try:
        # Inicia servidor ASGI
        uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
    finally:
        remove_pid()
        if tray_icon:
            try:
                stop_tray_icon()
            except Exception:
                pass
