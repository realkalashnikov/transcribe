import os
import sys
import re
import socket
import urllib.request
import subprocess
import threading
import atexit
import time
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.config import BIN_DIR, settings

class TunnelService:
    """
    Gerenciador do túnel seguro Cloudflare Quick Tunnel (sem necessidade de conta).
    Disponibiliza o Transcribe Studio na internet através de HTTPS válido.
    """

    _process: Optional[subprocess.Popen] = None
    _public_url: Optional[str] = None
    _is_starting: bool = False
    _lock = threading.Lock()

    @staticmethod
    def get_local_ip() -> str:
        """Descobre o endereço IP da máquina na rede local Wi-Fi / Ethernet."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    @classmethod
    def get_binary_path(cls) -> Path:
        """Retorna o caminho esperado do binário cloudflared."""
        exe_name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
        return BIN_DIR / exe_name

    @classmethod
    def ensure_cloudflared(cls) -> Path:
        """Verifica se o cloudflared existe no PATH ou em bin/. Se ausente, realiza o download seguro."""
        # 1. Verifica PATH do sistema
        import shutil
        path_binary = shutil.which("cloudflared")
        if path_binary:
            return Path(path_binary)

        # 2. Verifica pasta bin/ local
        local_binary = cls.get_binary_path()
        if local_binary.exists() and os.access(str(local_binary), os.X_OK | os.R_OK):
            return local_binary

        # 3. Download automático
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        elif sys.platform == "darwin":
            download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
        else:
            download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

        print(f"\n[Tunnel] Binário cloudflared não encontrado.")
        print(f"[Tunnel] Baixando release oficial de: {download_url}")
        print(f"[Tunnel] Salvando em: {local_binary} ...")

        def _reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\r[Tunnel] Download em progresso: {percent}% ({count * block_size // 1024 // 1024}MB / {total_size // 1024 // 1024}MB)")
                sys.stdout.flush()

        temp_target = local_binary.with_suffix(".tmp")
        try:
            urllib.request.urlretrieve(download_url, temp_target, reporthook=_reporthook)
            print("\n[Tunnel] Download concluído com sucesso!")
            if temp_target.exists():
                if local_binary.exists():
                    local_binary.unlink()
                temp_target.rename(local_binary)

            # Dá permissão de execução em Linux/Mac
            if sys.platform != "win32":
                os.chmod(str(local_binary), 0o755)

            return local_binary
        except Exception as e:
            if temp_target.exists():
                temp_target.unlink()
            raise RuntimeError(f"Falha ao baixar cloudflared: {e}")

    @classmethod
    def start_tunnel(cls, port: int = 8000, timeout: int = 30) -> Optional[str]:
        """
        Inicia o túnel Cloudflare para o porto especificado e extrai a URL HTTPS pública.
        """
        with cls._lock:
            if cls._public_url and cls._process and cls._process.poll() is None:
                return cls._public_url

            cls._is_starting = True

        binary_path = cls.ensure_cloudflared()
        cmd = [str(binary_path), "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"]

        print(f"[Tunnel] Iniciando túnel Cloudflare para 127.0.0.1:{port}...")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace"
        )
        cls._process = process

        url_found_event = threading.Event()
        extracted_url = [None]

        def _monitor_output(pipe):
            try:
                for line in iter(pipe.readline, ""):
                    if not line:
                        break
                    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                    if match:
                        extracted_url[0] = match.group(0)
                        url_found_event.set()
            except Exception:
                pass

        thread_err = threading.Thread(target=_monitor_output, args=(process.stderr,), daemon=True)
        thread_out = threading.Thread(target=_monitor_output, args=(process.stdout,), daemon=True)
        thread_err.start()
        thread_out.start()

        # Aguarda captura da URL verificando término prematuro do processo
        deadline = time.time() + timeout
        while time.time() < deadline:
            if url_found_event.wait(timeout=0.4):
                break
            if process.poll() is not None:
                print(f"[Tunnel] Processo cloudflared encerrou prematuramente (código: {process.returncode}).")
                break

        if extracted_url[0]:
            cls._public_url = extracted_url[0]
            cls._is_starting = False
            return cls._public_url

        cls._is_starting = False
        print("[Tunnel] Aviso: Não foi possível capturar a URL do túnel no tempo limite.")
        return None

    @classmethod
    def stop_tunnel(cls):
        """Finaliza o subprocesso do túnel se estiver em execução."""
        with cls._lock:
            if cls._process:
                print("[Tunnel] Encerrando túnel Cloudflare...")
                try:
                    cls._process.terminate()
                    cls._process.wait(timeout=3)
                except Exception:
                    try:
                        cls._process.kill()
                    except Exception:
                        pass
                cls._process = None
                cls._public_url = None

    @classmethod
    def get_info(cls, port: int = 8000) -> Dict[str, Any]:
        """Retorna informações estruturadas sobre conexões locais, de rede e túnel."""
        local_ip = cls.get_local_ip()
        return {
            "tunnel_active": bool(cls._public_url),
            "public_url": cls._public_url,
            "local_url": f"http://localhost:{port}",
            "lan_url": f"http://{local_ip}:{port}",
            "local_ip": local_ip,
            "port": port,
            "instance_mode": settings.instance_mode,
            "requires_pin": bool(settings.is_private and settings.access_pin),
            "access_pin": settings.access_pin if (settings.is_private and settings.access_pin) else None
        }

    @classmethod
    def print_banner(cls, port: int = 8000):
        """Imprime no terminal uma caixa elegante com links de acesso."""
        local_ip = cls.get_local_ip()
        pub_url = cls._public_url
        pin = settings.access_pin

        print("\n" + "=" * 65)
        print("   🚀 TRANSCRIBE STUDIO - SERVIÇO ATIVO")
        print("=" * 65)
        print(f"  Modo da Instância:   {settings.instance_mode.upper()}")
        print(f"  Acesso Local (PC):   http://localhost:{port}")
        print(f"  Rede Wi-Fi (LAN):    http://{local_ip}:{port}")

        if pub_url:
            mobile_url = f"{pub_url}?pin={pin}" if (pin and settings.is_private) else pub_url
            print(f"  Túnel Nuvem (HTTPS): {pub_url}")
            print(f"  Link Direto Celular: {mobile_url}")
        else:
            print(f"  Túnel Nuvem (HTTPS): Desativado (use --tunnel ou --share para ativar no PC)")

        if settings.is_private and pin:
            print(f"  PIN de Segurança:    {pin}")
        elif settings.is_public:
            print(f"  Acesso:              Público (Sessões isoladas permanentes)")

        print("=" * 65 + "\n")

# Registra encerramento automático do túnel quando a aplicação sair
atexit.register(TunnelService.stop_tunnel)
