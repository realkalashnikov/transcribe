import time
import hmac
import threading
from typing import Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

# Bloqueio de força bruta de PIN por IP
# client_ip -> (failed_attempts_count, lockout_until_timestamp)
_PIN_ATTEMPTS: Dict[str, Tuple[int, float]] = {}
_ATTEMPTS_LOCK = threading.Lock()

def record_pin_failure(client_ip: str) -> Tuple[int, float]:
    """Registra uma tentativa de PIN inválido e bloqueia se exceder 5 tentativas."""
    with _ATTEMPTS_LOCK:
        count, lockout = _PIN_ATTEMPTS.get(client_ip, (0, 0.0))
        now = time.time()
        if lockout > now:
            return count, lockout

        count += 1
        new_lockout = 0.0
        if count >= 5:
            new_lockout = now + 300.0  # 5 minutos de bloqueio
        _PIN_ATTEMPTS[client_ip] = (count, new_lockout)
        return count, new_lockout

def reset_pin_failures(client_ip: str):
    """Zera as tentativas de PIN ao acertar."""
    with _ATTEMPTS_LOCK:
        if client_ip in _PIN_ATTEMPTS:
            del _PIN_ATTEMPTS[client_ip]

def is_pin_locked(client_ip: str) -> Tuple[bool, int]:
    """Verifica se o IP está bloqueado temporariamente por força bruta."""
    with _ATTEMPTS_LOCK:
        count, lockout = _PIN_ATTEMPTS.get(client_ip, (0, 0.0))
        now = time.time()
        if lockout > now:
            return True, int(lockout - now)
        return False, 0

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware de Proteção por PIN / Senha.
    Ativo quando a instância está em modo 'private' com ACCESS_PIN definido.
    """

    PUBLIC_PATHS = {
        "/",
        "/favicon.ico",
        "/docs",
        "/openapi.json",
        "/api/info",
        "/api/v1/info",
        "/api/v1/status",
        "/api/tunnel/info",
        "/api/auth/verify"
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Permite rotas estáticas e de pré-voo OPTIONS
        if path.startswith("/static/") or request.method == "OPTIONS":
            return await call_next(request)

        # Se não há PIN exigido ou modo é público/byok, libera o tráfego
        if not settings.is_private or not settings.access_pin:
            return await call_next(request)

        # Se é rota explicitamente pública, libera
        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Identifica IP do cliente para proteção contra força bruta
        client_ip = request.client.host if request.client else "unknown"
        locked, remaining = is_pin_locked(client_ip)
        if locked:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Muitas tentativas incorretas de PIN. Tente novamente em {remaining}s.",
                    "retry_after_seconds": remaining
                },
                headers={"Retry-After": str(remaining)}
            )

        # Busca o PIN no header (X-Access-PIN ou Bearer), cookie ou query string
        auth_header = request.headers.get("authorization", "")
        bearer_pin = None
        if auth_header.lower().startswith("bearer "):
            bearer_pin = auth_header[7:].strip()

        provided_pin = (
            request.headers.get("x-access-pin")
            or bearer_pin
            or request.cookies.get("access_pin")
            or request.query_params.get("pin")
        )

        if not provided_pin or not hmac.compare_digest(provided_pin.strip(), settings.access_pin.strip()):
            record_pin_failure(client_ip)
            return JSONResponse(
                status_code=401,
                content={"detail": "PIN de acesso inválido ou ausente. Autenticação obrigatória."}
            )

        # PIN correto: zera contador de falhas
        reset_pin_failures(client_ip)
        return await call_next(request)
