import time
import threading
from collections import defaultdict, deque
from typing import Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware de Rate Limiting em memória.
    Protege o servidor contra sobrecarga ou scraping abusivo por IP e Sessão.
    """

    def __init__(self, app):
        super().__init__(app)
        # client_key -> deque of timestamps
        self._general_hits: Dict[str, deque] = defaultdict(deque)
        self._transcribe_hits: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    def _get_client_ip(self, request: Request) -> str:
        # Pega IP real (com suporte a Cloudflare / proxy reverso)
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self, now: float):
        """Remove registros com mais de 2 minutos para evitar vazamento de memória."""
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        cutoff = now - 60

        for key in list(self._general_hits.keys()):
            q = self._general_hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if not q:
                del self._general_hits[key]

        for key in list(self._transcribe_hits.keys()):
            q = self._transcribe_hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if not q:
                del self._transcribe_hits[key]

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Em modo privado ou chamadas locais de loopback, dispensa rate limit
        client_ip = self._get_client_ip(request)
        is_loopback = client_ip in ["127.0.0.1", "::1", "localhost", "testclient"]
        if settings.is_private or is_loopback:
            return await call_next(request)

        # Rotas isentas de rate limiting (assets, status e polling de status de job)
        if (
            path.startswith("/static/")
            or path.startswith("/api/jobs/")
            or path in ["/favicon.ico", "/docs", "/openapi.json", "/api/info", "/api/v1/status"]
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        client_key = client_ip
        now = time.time()

        with self._lock:
            self._cleanup_old_entries(now)

            # 1. Limite específico para transcrições pesadas
            is_heavy = path in ["/api/transcribe", "/api/jobs", "/api/v1/transcribe"]
            if is_heavy:
                t_hits = self._transcribe_hits[client_key]
                while t_hits and t_hits[0] < (now - 60):
                    t_hits.popleft()

                max_t = settings.transcribe_rate_limit_per_minute
                if len(t_hits) >= max_t:
                    retry_after = int(60 - (now - t_hits[0])) + 1
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Limite de transcrições atingido ({max_t}/min). Aguarde {retry_after}s.",
                            "retry_after_seconds": max(1, retry_after)
                        },
                        headers={"Retry-After": str(max(1, retry_after))}
                    )
                t_hits.append(now)

            # 2. Limite geral de requisições por minuto
            g_hits = self._general_hits[client_key]
            while g_hits and g_hits[0] < (now - 60):
                g_hits.popleft()

            max_g = settings.rate_limit_per_minute
            if len(g_hits) >= max_g:
                retry_after = int(60 - (now - g_hits[0])) + 1
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Limite de requisições excedido ({max_g}/min). Aguarde {retry_after}s.",
                        "retry_after_seconds": max(1, retry_after)
                    },
                    headers={"Retry-After": str(max(1, retry_after))}
                )
            g_hits.append(now)

        return await call_next(request)
