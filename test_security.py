import os
import sys
import time
import uuid
import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import settings, BASE_DIR, HISTORY_DIR, UPLOAD_DIR
from app.services.history import HistoryService
from app.services.cleaner import CleanerService
from app.services.concurrency import ConcurrencyGuard
from app.main import app

def test_session_isolation():
    print("[1/5] Testando isolamento de sessões...")
    session_a = f"test_user_a_{uuid.uuid4().hex[:8]}"
    session_b = f"test_user_b_{uuid.uuid4().hex[:8]}"

    job_a = f"job_a_{uuid.uuid4().hex[:8]}"
    job_b = f"job_b_{uuid.uuid4().hex[:8]}"

    # Salva item na sessão A
    HistoryService.save(
        job_id=job_a,
        filename="audio_a.mp3",
        result_dict={"text": "Texto confidencial de A", "language": "pt", "duration": 10.0},
        session_id=session_a
    )

    # Salva item na sessão B
    HistoryService.save(
        job_id=job_b,
        filename="audio_b.mp3",
        result_dict={"text": "Texto confidencial de B", "language": "en", "duration": 15.0},
        session_id=session_b
    )

    # Verifica list_all da sessão A
    items_a = HistoryService.list_all(session_id=session_a)
    assert any(it["id"] == job_a for it in items_a), "Job A deve estar na sessão A"
    assert not any(it["id"] == job_b for it in items_a), "Job B NÃO deve vazar para a sessão A"

    # Verifica get da sessão A
    assert HistoryService.get(job_a, session_id=session_a) is not None
    # Força modo público para testar barreira estrita
    original_mode = settings.instance_mode
    settings.instance_mode = "public"
    try:
        assert HistoryService.get(job_b, session_id=session_a) is None, "Sessão A não pode ler job B em modo público"
    finally:
        settings.instance_mode = original_mode

    # Limpeza
    HistoryService.delete(job_a, session_id=session_a)
    HistoryService.delete(job_b, session_id=session_b)
    print(" -> Isolamento de sessão validado com sucesso!")

def test_auth_middleware():
    print("[2/5] Testando middleware de autenticação (PIN)...")
    original_mode = settings.instance_mode
    original_pin = settings.access_pin

    settings.instance_mode = "private"
    settings.access_pin = "998877"

    client = TestClient(app)

    try:
        # Rota pública /api/info deve passar sem PIN
        resp = client.get("/api/info")
        assert resp.status_code == 200, f"Status esperado 200, obtido {resp.status_code}"

        # Rota protegida /api/history sem PIN deve retornar 401
        resp = client.get("/api/history")
        assert resp.status_code == 401, f"Status esperado 401, obtido {resp.status_code}"

        # Rota protegida com PIN incorreto deve retornar 401
        resp = client.get("/api/history", headers={"X-Access-PIN": "000000"})
        assert resp.status_code == 401, f"Status esperado 401, obtido {resp.status_code}"

        # Rota protegida com PIN correto deve retornar 200
        resp = client.get("/api/history", headers={"X-Access-PIN": "998877"})
        assert resp.status_code == 200, f"Status esperado 200, obtido {resp.status_code}"

        # Verificação via /api/auth/verify
        resp_verify_err = client.post("/api/auth/verify", json={"pin": "errado"})
        assert resp_verify_err.status_code == 401

        resp_verify_ok = client.post("/api/auth/verify", json={"pin": "998877"})
        assert resp_verify_ok.status_code == 200
        assert resp_verify_ok.json().get("authenticated") is True

    finally:
        settings.instance_mode = original_mode
        settings.access_pin = original_pin

    print(" -> Middleware de autenticação validado com sucesso!")

def test_rate_limiting():
    print("[3/5] Testando middleware de Rate Limiting...")
    original_rate = settings.rate_limit_per_minute
    settings.rate_limit_per_minute = 5

    client = TestClient(app)
    try:
        # Executa 5 requisições rápidas permitidas
        for i in range(5):
            r = client.get("/api/history", headers={"X-Session-ID": "test_rl_session"})
            assert r.status_code in [200, 401], f"Status inesperado: {r.status_code}"

        # A 6ª deve receber 429 Too Many Requests
        r6 = client.get("/api/history", headers={"X-Session-ID": "test_rl_session"})
        assert r6.status_code == 429, f"Status esperado 429, recebido {r6.status_code}"
        assert "Retry-After" in r6.headers
    finally:
        settings.rate_limit_per_minute = original_rate

    print(" -> Rate Limiter validado com sucesso (HTTP 429 retornado)!")

def test_cleaner_service():
    print("[4/5] Testando serviço de limpeza efêmera (CleanerService)...")
    # Cria arquivo fictício em uploads com mtime no passado
    fake_upload = UPLOAD_DIR / "fake_old_upload.tmp"
    with open(fake_upload, "w") as f:
        f.write("dados temporarios")

    # Altera mtime para 20 minutos atrás
    old_time = time.time() - (20 * 60)
    os.utime(fake_upload, (old_time, old_time))

    cleaned = CleanerService.clean_uploads(max_age_minutes=15)
    assert cleaned >= 1, "Cleaner deve ter removido o upload expirado"
    assert not fake_upload.exists(), "Arquivo expirado deve ter sido deletado"

    print(" -> CleanerService validado com sucesso!")

def test_concurrency_guard():
    print("[5/5] Testando ConcurrencyGuard...")
    assert ConcurrencyGuard.acquire() is True
    stats = ConcurrencyGuard.get_stats()
    assert stats["active_jobs"] >= 1
    ConcurrencyGuard.release()
    print(" -> ConcurrencyGuard validado com sucesso!")

if __name__ == "__main__":
    test_session_isolation()
    test_auth_middleware()
    test_rate_limiting()
    test_cleaner_service()
    test_concurrency_guard()
    print("\n[SUCESSO] TODOS OS TESTES DE SEGURANÇA E ISOLAMENTO PASSARAM!")
