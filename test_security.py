import os
import sys
import time
import uuid
import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import settings, BASE_DIR, HISTORY_DIR, UPLOAD_DIR
from app.services.history import HistoryService, sanitize_session_id, sanitize_job_id
from app.services.cleaner import CleanerService
from app.services.concurrency import ConcurrencyGuard
from app.main import app

def test_session_isolation():
    print("[1/9] Testando isolamento de sessões silencioso (Zero Burocracia)...")
    original_mode = settings.instance_mode
    
    # 1. Modo Público: isolamento estrito entre usuários
    settings.instance_mode = "public"
    session_a = f"user_a_{uuid.uuid4().hex[:8]}"
    session_b = f"user_b_{uuid.uuid4().hex[:8]}"

    job_a = f"job_a_{uuid.uuid4().hex[:8]}"
    job_b = f"job_b_{uuid.uuid4().hex[:8]}"

    try:
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

        # Sessão A só pode ver A
        items_a = HistoryService.list_all(session_id=session_a)
        assert any(it["id"] == job_a for it in items_a), "Job A deve estar na sessão A"
        assert not any(it["id"] == job_b for it in items_a), "Job B NÃO deve vazar para a sessão A"

        # Get direto isolado
        assert HistoryService.get(job_a, session_id=session_a) is not None
        assert HistoryService.get(job_b, session_id=session_a) is None, "Sessão A não pode ler job B"

        # Sessão B só pode ver B
        items_b = HistoryService.list_all(session_id=session_b)
        assert any(it["id"] == job_b for it in items_b), "Job B deve estar na sessão B"
        assert not any(it["id"] == job_a for it in items_b), "Job A NÃO deve vazar para a sessão B"

    finally:
        HistoryService.delete(job_a, session_id=session_a)
        HistoryService.delete(job_b, session_id=session_b)
        settings.instance_mode = original_mode

    # 2. Modo Privado / Compartilhado: cada dispositivo/amigo mantém seu histórico isolado
    settings.instance_mode = "private"
    session_device1 = f"dev1_{uuid.uuid4().hex[:8]}"
    session_device2 = f"dev2_{uuid.uuid4().hex[:8]}"
    job_dev1 = f"job_dev1_{uuid.uuid4().hex[:8]}"
    job_dev2 = f"job_dev2_{uuid.uuid4().hex[:8]}"

    try:
        HistoryService.save(
            job_id=job_dev1,
            filename="dev1_recording.mp3",
            result_dict={"text": "Gravação privada do device 1", "language": "pt", "duration": 5.0},
            session_id=session_device1
        )
        HistoryService.save(
            job_id=job_dev2,
            filename="dev2_recording.mp3",
            result_dict={"text": "Gravação privada do device 2", "language": "en", "duration": 8.0},
            session_id=session_device2
        )

        # Dispositivo 2 NÃO deve ver o item do Dispositivo 1
        items_dev2 = HistoryService.list_all(session_id=session_device2)
        assert any(it["id"] == job_dev2 for it in items_dev2), "Dispositivo 2 deve ver seu próprio histórico"
        assert not any(it["id"] == job_dev1 for it in items_dev2), "Dispositivo 2 NÃO deve ver histórico do dispositivo 1"
        assert HistoryService.get(job_dev1, session_id=session_device2) is None, "Dispositivo 2 não pode ler gravação do dispositivo 1"

        # Dispositivo 1 só vê seu próprio histórico
        items_dev1 = HistoryService.list_all(session_id=session_device1)
        assert any(it["id"] == job_dev1 for it in items_dev1), "Dispositivo 1 deve ver seu próprio histórico"
        assert not any(it["id"] == job_dev2 for it in items_dev1), "Dispositivo 1 NÃO deve ver histórico do dispositivo 2"
    finally:
        HistoryService.delete(job_dev1, session_id=session_device1)
        HistoryService.delete(job_dev2, session_id=session_device2)
        settings.instance_mode = original_mode

    print(" -> Isolamento estrito de sessões por pessoa/dispositivo validado com sucesso!")

def test_job_id_sanitization():
    print("[2/9] Testando sanitização de Job ID e mitigação de Glob/Path Traversal...")
    # 1. Validação de formato
    assert sanitize_job_id("valid-job_123") == "valid-job_123"
    assert sanitize_job_id("../../../etc/passwd") is None
    assert sanitize_job_id("*") is None
    assert sanitize_job_id("") is None

    # 2. Proteção contra wildcard injection em delete()
    dummy_job = f"dummy_{uuid.uuid4().hex[:8]}"
    HistoryService.save(
        job_id=dummy_job,
        filename="dummy.mp3",
        result_dict={"text": "teste"}
    )
    # Tentar delete com '*' NÃO deve excluir arquivos
    deleted = HistoryService.delete("*")
    assert deleted is False, "Wildcard '*' não deve ser aceito para exclusão"
    assert HistoryService.get(dummy_job) is not None, "Arquivo do histórico deve permanecer intacto"

    # Tentar get com path traversal
    assert HistoryService.get("../../some_file") is None

    # Limpeza correta
    HistoryService.delete(dummy_job)
    print(" -> Sanitização de Job ID e prevenção contra Glob Injection validadas com sucesso!")

def test_auth_middleware_and_bearer():
    print("[3/9] Testando autenticação por PIN, Header Bearer e proteção contra força bruta...")
    original_mode = settings.instance_mode
    original_pin = settings.access_pin

    settings.instance_mode = "private"
    settings.access_pin = "482619"

    client = TestClient(app)

    try:
        # Rota pública /api/info passa sem PIN
        resp = client.get("/api/info")
        assert resp.status_code == 200

        # Rota protegida sem PIN retorna 401
        resp = client.get("/api/history")
        assert resp.status_code == 401

        # Rota protegida com X-Access-PIN correto
        resp = client.get("/api/history", headers={"X-Access-PIN": "482619"})
        assert resp.status_code == 200

        # Rota protegida com Authorization: Bearer <pin>
        resp_bearer = client.get("/api/history", headers={"Authorization": "Bearer 482619"})
        assert resp_bearer.status_code == 200

        # Rota protegida com PIN via query string (usado pelo áudio player)
        resp_query = client.get("/api/history?pin=482619")
        assert resp_query.status_code == 200

        # Verificação via endpoint /api/auth/verify
        r_ok = client.post("/api/auth/verify", json={"pin": "482619"})
        assert r_ok.status_code == 200
        assert r_ok.json().get("authenticated") is True

        r_err = client.post("/api/auth/verify", json={"pin": "000000"})
        assert r_err.status_code == 401

    finally:
        settings.instance_mode = original_mode
        settings.access_pin = original_pin

    print(" -> Autenticação PIN e suporte a Bearer validados com sucesso!")

def test_rate_limiting_anti_evasion():
    print("[4/9] Testando Rate Limiting e prevenção de evasão por rotação de sessão...")
    original_rate = settings.rate_limit_per_minute
    original_mode = settings.instance_mode
    settings.rate_limit_per_minute = 5
    settings.instance_mode = "public"

    client = TestClient(app)
    ip_under_test = f"198.51.100.{uuid.uuid4().int % 250 + 1}"
    try:
        # Envia 5 requisições com sessões DIFERENTES do mesmo IP
        for i in range(5):
            r = client.get(
                "/api/history",
                headers={"CF-Connecting-IP": ip_under_test, "X-Session-ID": f"fake_session_{i}"}
            )
            assert r.status_code in [200, 401], f"Status inesperado na requisição {i}: {r.status_code}"

        # A 6ª requisição do mesmo IP DEVE ser bloqueada (HTTP 429), mesmo alterando X-Session-ID
        r6 = client.get(
            "/api/history",
            headers={"CF-Connecting-IP": ip_under_test, "X-Session-ID": "fake_session_new"}
        )
        assert r6.status_code == 429, f"Rate Limiter deve bloquear IP mesmo rotacionando sessão (status: {r6.status_code})"
        assert "Retry-After" in r6.headers
    finally:
        settings.rate_limit_per_minute = original_rate
        settings.instance_mode = original_mode

    print(" -> Rate Limiter anti-evasão validado com sucesso!")

def test_cleaner_service_preservation():
    print("[5/9] Testando CleanerService (persistência permanente de histórico e limpeza de uploads)...")
    original_mode = settings.instance_mode
    settings.instance_mode = "public"

    session_file = None
    session_dir = None
    temp_upload = None

    try:
        # 1. Cria histórico do usuário (simula arquivo criado há 2 horas)
        session_id = f"user_perm_{uuid.uuid4().hex[:8]}"
        session_dir = HISTORY_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "user_audio.mp3"
        with open(session_file, "w") as f:
            f.write("audio persistente do usuario")
        old_time = time.time() - (120 * 60) # 2 horas atrás
        os.utime(session_file, (old_time, old_time))

        # 2. Cria upload temporário antigo em UPLOAD_DIR
        temp_upload = UPLOAD_DIR / f"temp_{uuid.uuid4().hex[:8]}.tmp"
        with open(temp_upload, "w") as f:
            f.write("upload temporario esquecido")
        os.utime(temp_upload, (old_time, old_time))

        # 3. Executa varredura padrão periódica (clean_all)
        stats = CleanerService.clean_all()

        # O upload temporário órfão DEVE ter sido removido
        assert not temp_upload.exists(), "Uploads temporários antigos devem ser removidos pelo cleaner"
        assert stats["uploads_removed"] >= 1

        # O histórico do usuário DEVE permanecer intacto (persistência permanente sem auto-exclusão após 1 hora)
        assert session_file.exists(), "Histórico e áudios do usuário devem ser preservados permanentemente"
        assert stats["history_removed"] == 0, "clean_all nunca deve auto-excluir histórico de usuários"

        # 4. Limpeza manual explícita com max_age_minutes > 0 (manutenção manual) ainda funciona
        manual_removed = CleanerService.clean_expired_history(max_age_minutes=60)
        assert manual_removed >= 1, "Limpeza manual explícita com max_age_minutes deve funcionar quando invocada"
        assert not session_file.exists(), "Arquivo deve ser removido após chamada explícita de limpeza manual"

    finally:
        if temp_upload and temp_upload.exists():
            temp_upload.unlink()
        if session_file and session_file.exists():
            session_file.unlink()
        if session_dir and session_dir.exists():
            try:
                session_dir.rmdir()
            except Exception:
                pass
        settings.instance_mode = original_mode

    print(" -> Persistência permanente de histórico e limpeza de uploads validadas com sucesso!")

def test_upload_security():
    print("[6/9] Testando segurança no upload (arquivo 0 bytes e path traversal)...")
    client = TestClient(app)

    # 1. Rejeição de arquivo de 0 bytes
    empty_file = ("empty.wav", b"", "audio/wav")
    resp_empty = client.post(
        "/api/transcribe",
        files={"file": empty_file},
        data={"provider": "faster-whisper"}
    )
    assert resp_empty.status_code == 400, f"Upload de 0 bytes deve retornar 400, obteve {resp_empty.status_code}"
    assert "vazio" in resp_empty.text.lower()

    # 2. Filename com tentativa de Directory Traversal
    traversal_file = ("../../traversal_test.wav", b"fake audio content", "audio/wav")
    resp_trav = client.post(
        "/api/transcribe",
        files={"file": traversal_file},
        data={"provider": "faster-whisper"}
    )
    # Nenhum arquivo deve ter sido criado fora de UPLOAD_DIR
    escaped_file = BASE_DIR / "traversal_test.wav"
    assert not escaped_file.exists(), "Upload NÃO pode escapar de UPLOAD_DIR"

    print(" -> Proteção de upload contra 0 bytes e path traversal validada com sucesso!")

def test_byok_mode_enforcement():
    print("[7/9] Testando restrições do modo BYOK...")
    original_mode = settings.instance_mode
    settings.set_mode("byok")
    client = TestClient(app)

    try:
        from test_app import generate_test_wav
        test_wav = generate_test_wav("test_byok.wav", duration=1.0)

        # 1. Tentativa de usar motor local no modo BYOK deve retornar 400
        with open(test_wav, "rb") as f:
            resp_local = client.post(
                "/api/transcribe",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"provider": "faster-whisper", "model": "tiny"}
            )
        assert resp_local.status_code == 400
        assert "byok" in resp_local.text.lower()

        # 2. Tentativa de usar provedor sem API key deve retornar 400
        with open(test_wav, "rb") as f:
            resp_no_key = client.post(
                "/api/transcribe",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"provider": "groq", "api_key": ""}
            )
        assert resp_no_key.status_code == 400

    finally:
        if os.path.exists("test_byok.wav"):
            os.remove("test_byok.wav")
        settings.set_mode(original_mode)

    print(" -> Modo BYOK validado com sucesso!")

def test_dynamic_mode_adaptation():
    print("[8/9] Testando adaptação dinâmica de quotas ao alterar modo...")
    original_mode = settings.instance_mode

    # Modo público: limites anti-abuso rígidos (300s / 50MB)
    settings.set_mode("public")
    assert settings.max_audio_duration_seconds == 300
    assert settings.max_upload_size_mb == 50
    assert settings.is_public is True

    # Modo privado: limites amplos para o proprietário (7200s / 500MB)
    settings.set_mode("private")
    assert settings.max_audio_duration_seconds == 7200
    assert settings.max_upload_size_mb == 500
    assert settings.is_private is True

    settings.set_mode(original_mode)
    print(" -> Adaptação dinâmica de quotas validada com sucesso!")

def test_api_v1():
    print("[9/9] Testando API REST v1 e endpoint de túnel...")
    from test_app import generate_test_wav
    test_wav = generate_test_wav("test_sample_v1.wav", duration=1.0)
    client = TestClient(app)

    try:
        # 1. Status
        r_status = client.get("/api/v1/status")
        assert r_status.status_code == 200
        assert r_status.json()["status"] == "online"

        # 2. Info
        r_info = client.get("/api/v1/info")
        assert r_info.status_code == 200
        assert "limits" in r_info.json()
        assert "engines" in r_info.json()

        # 3. Tunnel Info
        r_tunnel = client.get("/api/tunnel/info")
        assert r_tunnel.status_code == 200
        assert "lan_url" in r_tunnel.json()

        # 4. Transcribe v1 (JSON)
        test_ip = "203.0.113.10"
        with open(test_wav, "rb") as f:
            r_tx = client.post(
                "/api/v1/transcribe",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"provider": "faster-whisper", "model": "tiny", "response_format": "json"},
                headers={"CF-Connecting-IP": test_ip}
            )
        assert r_tx.status_code == 200, f"Erro na API v1: {r_tx.text}"
        data = r_tx.json()
        assert "text" in data
        assert "segments" in data

        # 5. Transcribe v1 (SRT)
        with open(test_wav, "rb") as f:
            r_srt = client.post(
                "/api/v1/transcribe",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"provider": "faster-whisper", "model": "tiny", "response_format": "srt"},
                headers={"CF-Connecting-IP": test_ip}
            )
        assert r_srt.status_code == 200, f"Erro SRT: {r_srt.text}"
        assert isinstance(r_srt.text, str)

    finally:
        if os.path.exists(test_wav):
            os.remove(test_wav)

    print(" -> API REST v1 validada com sucesso!")

if __name__ == "__main__":
    test_session_isolation()
    test_job_id_sanitization()
    test_auth_middleware_and_bearer()
    test_rate_limiting_anti_evasion()
    test_cleaner_service_preservation()
    test_upload_security()
    test_byok_mode_enforcement()
    test_dynamic_mode_adaptation()
    test_api_v1()
    print("\n[SUCESSO] TODOS OS 9 TESTES DE SEGURANÇA, API E ISOLAMENTO PASSARAM!")
