import os
import re
import socket
import ipaddress
import urllib.parse
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

import yt_dlp
from app.core.config import UPLOAD_DIR, settings

class SSRFError(Exception):
    """Exceção levantada quando uma URL aponta para endereço privado, loopback ou não autorizado."""
    pass

def is_safe_url(url: str) -> Tuple[bool, str]:
    """
    Escudo Anti-SSRF Rigoroso:
    Valida se a URL é pública e segura, bloqueando:
    - Esquemas não HTTP/HTTPS (file://, gopher://, ftp://, etc.)
    - IPs privados (RFC 1918: 10.x, 172.16-31.x, 192.168.x)
    - Loopback (127.0.0.1, localhost, ::1)
    - Endereços Link-Local e Metadados de Nuvem (169.254.169.254, fe80::)
    - Portas não padrão (permite apenas 80, 443 e sem porta explícita)
    """
    if not url or not isinstance(url, str):
        return False, "URL vazia ou inválida."

    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        return False, f"URL malformada: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Esquema não suportado: '{parsed.scheme}'. Apenas HTTP e HTTPS são permitidos."

    hostname = parsed.hostname
    if not hostname:
        return False, "Hostname ausente na URL."

    # Bloqueia hostnames locais explícitos
    lower_host = hostname.lower()
    if lower_host in ("localhost", "localhost.localdomain") or lower_host.endswith((".local", ".localhost", ".internal", ".lan")):
        return False, "Acesso a endereços locais e de rede interna é estritamente proibido."

    # Valida porta
    port = parsed.port
    if port and port not in (80, 443):
        return False, f"Porta não permitida: {port}. Apenas portas web padrão (80 e 443) são aceitas."

    # Resolução de DNS e inspeção de IP
    try:
        # Resolve todos os registros IPv4 e IPv6
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, f"Não foi possível resolver o domínio '{hostname}'."
    except Exception as e:
        return False, f"Erro na resolução de DNS: {e}"

    if not addr_info:
        return False, "Nenhum endereço IP associado ao domínio informado."

    for family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Endereço IP inválido detectado: '{ip_str}'."

        if ip_obj.is_loopback:
            return False, "Acesso a endereços de loopback (127.0.0.1, ::1) é proibido."
        if ip_obj.is_private:
            return False, "Acesso a redes privadas (RFC 1918) é proibido."
        if ip_obj.is_link_local:
            return False, "Acesso a endereços link-local é proibido."
        if ip_obj.is_multicast:
            return False, "Acesso a endereços multicast é proibido."
        if ip_obj.is_reserved:
            return False, "Acesso a endereços reservados é proibido."
        # Proteção explícita contra metadados AWS/GCP/Azure
        if str(ip_obj) == "169.254.169.254":
            return False, "Acesso aos endpoints de metadados de nuvem é estritamente bloqueado."

    return True, "URL segura."

class MediaDownloader:
    """
    Serviço de Ingestão de Áudio e Vídeo a partir de URLs públicas
    (YouTube, Twitter/X, SoundCloud, TikTok, etc.) usando yt-dlp.
    """

    @staticmethod
    def download_url(
        url: str,
        output_dir: Optional[Path] = None,
        max_duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Valida a URL contra SSRF, extrai informações e baixa o áudio.
        Retorna dicionário com 'file_path', 'title', 'duration' e 'original_url'.
        """
        is_safe, reason = is_safe_url(url)
        if not is_safe:
            raise SSRFError(reason)

        target_dir = output_dir or UPLOAD_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        max_dur = max_duration_seconds or settings.max_audio_duration_seconds

        # Configuração do yt-dlp
        # Preferimos formatos de áudio diretos (m4a, mp3, opus, webm) decodificáveis por PyAV
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(target_dir / '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'max_filesize': settings.max_upload_size_bytes,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extrai metadados antes de baixar para validar limites
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                raise ValueError(f"Não foi possível obter informações da mídia: {e}")

            if not info:
                raise ValueError("Nenhuma informação de mídia encontrada na URL.")

            duration = info.get('duration') or 0
            if max_dur and max_dur > 0 and duration > max_dur:
                raise ValueError(
                    f"A duração do áudio ({duration:.0f}s) excede o limite máximo permitido da instância ({max_dur}s / {max_dur//60} min)."
                )

            # 2. Realiza o download
            try:
                downloaded_info = ydl.extract_info(url, download=True)
            except Exception as e:
                raise ValueError(f"Falha ao baixar o áudio: {e}")

            filename = ydl.prepare_filename(downloaded_info)
            # Verifica se o arquivo final existe
            file_path = Path(filename)
            if not file_path.exists():
                # Tenta localizar com extensão diferente caso o yt-dlp tenha ajustado
                base_name = file_path.stem
                found = list(target_dir.glob(f"{base_name}.*"))
                if found:
                    file_path = found[0]
                else:
                    raise FileNotFoundError("Arquivo baixado não foi localizado no disco.")

            title = info.get('title') or file_path.stem
            # Sanitiza título para nome de arquivo amigável
            clean_title = re.sub(r'[^\w\s\.-]', '', title).strip() or "audio_url"

            return {
                "file_path": str(file_path),
                "title": clean_title,
                "duration": float(duration),
                "original_url": url,
                "uploader": info.get('uploader') or ""
            }
