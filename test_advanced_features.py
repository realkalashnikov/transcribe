import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.downloader import is_safe_url, SSRFError, MediaDownloader
from app.services.llm_actions import LLMActionService
from app.services.history import HistoryService

class TestAdvancedFeatures(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_ssrf_protection(self):
        """Verifica se o escudo anti-SSRF bloqueia estritamente requisições maliciosas."""
        blocked_urls = [
            "http://localhost:8000/api/info",
            "http://127.0.0.1:8000/api/history",
            "http://192.168.1.1/admin",
            "http://10.0.0.1/secret",
            "http://172.16.0.5/api",
            "http://169.254.169.254/latest/meta-data/",
            "ftp://files.example.com/audio.mp3",
            "file:///etc/passwd",
            "http://localhost.localdomain/test",
            "https://test.local/media.wav",
            "http://google.com:22/audio.mp3", # Porta não padrão
        ]
        for url in blocked_urls:
            is_safe, reason = is_safe_url(url)
            self.assertFalse(is_safe, f"URL deveria ser bloqueada: {url} (Motivo: {reason})")

        # URL pública válida
        is_safe, _ = is_safe_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertTrue(is_safe, "URL pública segura do YouTube deve ser permitida.")

    def test_inline_editing_history(self):
        """Valida que HistoryService.update atualiza o texto, segmentos e exports sem corromper o arquivo."""
        test_job = "test_edit_job_123"
        session_id = "test_edit_session"

        try:
            # 1. Cria item inicial
            HistoryService.save(
                job_id=test_job,
                filename="original.mp3",
                result_dict={
                    "text": "Texto original com erro ortografico",
                    "language": "pt",
                    "duration": 5.0,
                    "segments": [
                        {"id": 1, "start": 0.0, "end": 5.0, "text": "Texto original com erro ortografico"}
                    ]
                },
                session_id=session_id
            )

            # 2. Executa atualização inline
            updated_segments = [
                {"id": 1, "start": 0.0, "end": 5.0, "text": "Texto corrigido e revisado perfeitamente."}
            ]
            updated_item = HistoryService.update(
                job_id=test_job,
                updated_segments=updated_segments,
                session_id=session_id
            )

            self.assertIsNotNone(updated_item)
            self.assertEqual(updated_item["text"], "Texto corrigido e revisado perfeitamente.")
            self.assertIn("Texto corrigido e revisado perfeitamente.", updated_item["exports"]["srt"])
            self.assertIn("Texto corrigido e revisado perfeitamente.", updated_item["exports"]["vtt"])
            self.assertIn("Texto corrigido e revisado perfeitamente.", updated_item["exports"]["txt"])

            # 3. Teste via endpoint PUT /api/history/{job_id}
            resp = self.client.put(
                f"/api/history/{test_job}",
                json={"text": "Texto via PUT atualizado."},
                headers={"X-Session-ID": session_id}
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["item"]["text"], "Texto via PUT atualizado.")

        finally:
            HistoryService.delete(test_job, session_id=session_id)

    @patch.object(LLMActionService, "process_action")
    def test_llm_action_service(self, mock_process):
        """Valida a orquestração do LLMActionService com resposta formatada."""
        mock_process.return_value = {
            "result": "Este é o resumo executivo gerado pela LLM.",
            "action": "summary",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile"
        }

        # Teste chamada via endpoint POST /api/summarize
        resp = self.client.post(
            "/api/summarize",
            json={
                "text": "Transcrição para ata.",
                "action": "summary",
                "provider": "groq",
                "api_key": "gsk_fake_key_123"
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], "Este é o resumo executivo gerado pela LLM.")
        mock_process.assert_called_once()

    def test_ssrf_endpoint_blocked(self):
        """Verifica se o endpoint POST /api/ingest/url rejeita tentativas de SSRF com HTTP 400."""
        resp = self.client.post(
            "/api/ingest/url",
            json={"url": "http://127.0.0.1:8000/api/info"}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("SSRF", resp.json()["detail"])

    def test_transliteration_service_and_endpoint(self):
        """Verifica a romanização de Japonês, Chinês e Russo tanto na classe quanto no endpoint."""
        from app.services.transliteration import TransliterationService

        # Japonês
        ja_rom = TransliterationService.romanize("こんにちは世界", "ja")
        self.assertIn("konnichiha", ja_rom.lower())

        # Cirílico (Russo)
        ru_rom = TransliterationService.romanize("Привет мир", "ru")
        self.assertEqual(ru_rom, "Privet mir")

        # Endpoint POST /api/romanize
        resp = self.client.post(
            "/api/romanize",
            json={
                "text": "こんにちは",
                "language": "ja",
                "segments": [
                    {"id": 1, "start": 0.0, "end": 1.5, "text": "こんにちは"}
                ]
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("konnichiha", data["romanized_text"].lower())
        self.assertIsNotNone(data["segments"])
        self.assertIn("konnichiha", data["segments"][0]["romanized"].lower())

    def test_video_muxer_availability(self):
        """Verifica se o VideoMuxer detecta o binário do FFmpeg corretamente."""
        from app.services.video_muxer import VideoMuxer
        self.assertTrue(VideoMuxer.is_available(), "FFmpeg deve estar disponível via imageio-ffmpeg ou sistema.")

if __name__ == "__main__":
    unittest.main()

