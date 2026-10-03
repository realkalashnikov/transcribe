import os
import io
import json
import base64
from typing import Optional, Callable, Dict, Any
import httpx

from app.engine.base import BaseTranscriber, TranscriptionResult, TranscriptionSegment
from app.engine.faster_whisper import get_audio_duration

class CloudTranscriber(BaseTranscriber):
    """
    Motor para provedores de transcrição em Nuvem:
    - Groq (Whisper-large-v3 / turbo)
    - OpenAI (Whisper-1)
    - Google Gemini (Gemini 2.5 Flash / 1.5 Flash)
    """

    def __init__(self, provider: str, api_key: str, model: Optional[str] = None, base_url: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = (api_key or "").strip()
        self.model = model
        self.base_url = (base_url or "").strip()

    def transcribe(
        self,
        file_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        **kwargs
    ) -> TranscriptionResult:
        if not self.api_key and self.provider not in ("custom", "openai_compatible"):
            raise ValueError(f"A chave de API para o provedor '{self.provider}' não foi fornecida.")

        clean_prompt = (prompt.strip()[:500]) if (prompt and prompt.strip()) else None

        if self.provider == "groq":
            return self._transcribe_groq(file_path, language, clean_prompt, progress_callback)
        elif self.provider == "openai":
            return self._transcribe_openai(file_path, language, clean_prompt, progress_callback)
        elif self.provider == "gemini":
            return self._transcribe_gemini(file_path, language, clean_prompt, progress_callback)
        elif self.provider in ("custom", "openai_compatible"):
            return self._transcribe_custom_openai(file_path, language, clean_prompt, progress_callback)
        else:
            raise ValueError(f"Provedor desconhecido: {self.provider}")

    def _transcribe_custom_openai(
        self,
        file_path: str,
        language: Optional[str],
        prompt: Optional[str],
        progress_callback: Optional[Callable[[float, str], None]]
    ) -> TranscriptionResult:
        if progress_callback:
            progress_callback(10.0, "Enviando áudio para Endpoint Personalizado...")

        model_name = self.model or "whisper-1"
        base = self.base_url or "http://localhost:11434/v1"
        endpoint = f"{base.rstrip('/')}/audio/transcriptions" if not base.endswith("/audio/transcriptions") else base
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        files = {"file": (filename, file_bytes)}
        data = {
            "model": model_name,
            "response_format": "verbose_json"
        }
        if language and language.strip().lower() != "auto":
            data["language"] = language.strip()
        if prompt:
            data["prompt"] = prompt

        if progress_callback:
            progress_callback(40.0, f"Processando transcrição no endpoint ({model_name})...")

        with httpx.Client(timeout=300.0) as client:
            resp = client.post(endpoint, headers=headers, files=files, data=data)

        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(f"Erro no provedor personalizado ({resp.status_code}): {err_msg}")

        result_data = resp.json()
        return self._parse_openai_format_response(result_data, file_path, f"custom-{model_name}", "custom", progress_callback)

    def _transcribe_groq(
        self,
        file_path: str,
        language: Optional[str],
        prompt: Optional[str],
        progress_callback: Optional[Callable[[float, str], None]]
    ) -> TranscriptionResult:
        if progress_callback:
            progress_callback(10.0, "Enviando áudio para Groq Whisper...")

        model_name = self.model or "whisper-large-v3-turbo"
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        files = {"file": (filename, file_bytes)}
        data = {
            "model": model_name,
            "response_format": "verbose_json"
        }
        if language and language.strip().lower() != "auto":
            data["language"] = language.strip()
        if prompt:
            data["prompt"] = prompt

        if progress_callback:
            progress_callback(40.0, f"Processando transcrição na Groq ({model_name})...")

        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, headers=headers, files=files, data=data)

        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(f"Erro na API Groq ({resp.status_code}): {err_msg}")

        result_data = resp.json()
        return self._parse_openai_format_response(result_data, file_path, f"groq-{model_name}", "groq", progress_callback)

    def _transcribe_openai(
        self,
        file_path: str,
        language: Optional[str],
        prompt: Optional[str],
        progress_callback: Optional[Callable[[float, str], None]]
    ) -> TranscriptionResult:
        if progress_callback:
            progress_callback(10.0, "Enviando áudio para OpenAI Whisper...")

        model_name = self.model or "whisper-1"
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        files = {"file": (filename, file_bytes)}
        data = {
            "model": model_name,
            "response_format": "verbose_json"
        }
        if language and language.strip().lower() != "auto":
            data["language"] = language.strip()
        if prompt:
            data["prompt"] = prompt

        if progress_callback:
            progress_callback(40.0, "Processando transcrição na OpenAI...")

        with httpx.Client(timeout=300.0) as client:
            resp = client.post(url, headers=headers, files=files, data=data)

        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(f"Erro na API OpenAI ({resp.status_code}): {err_msg}")

        result_data = resp.json()
        return self._parse_openai_format_response(result_data, file_path, f"openai-{model_name}", "openai", progress_callback)

    def _parse_openai_format_response(
        self,
        data: Dict[str, Any],
        file_path: str,
        model_name: str,
        provider_name: str,
        progress_callback: Optional[Callable[[float, str], None]]
    ) -> TranscriptionResult:
        segments_list = []
        raw_segments = data.get("segments", [])

        if raw_segments:
            for s in raw_segments:
                segments_list.append(TranscriptionSegment(
                    id=s.get("id", len(segments_list) + 1),
                    start=round(float(s.get("start", 0.0)), 2),
                    end=round(float(s.get("end", 0.0)), 2),
                    text=s.get("text", "").strip()
                ))
        else:
            # Caso não venham segmentos divididos, cria um segmento único
            full_txt = data.get("text", "").strip()
            total_dur = get_audio_duration(file_path)
            if full_txt:
                segments_list.append(TranscriptionSegment(
                    id=1,
                    start=0.0,
                    end=total_dur,
                    text=full_txt
                ))

        if progress_callback:
            progress_callback(100.0, "Transcrição finalizada com sucesso!")

        return TranscriptionResult(
            text=data.get("text", "").strip(),
            segments=segments_list,
            language=data.get("language", "auto"),
            duration=float(data.get("duration", get_audio_duration(file_path))),
            model=model_name,
            provider=provider_name
        )

    def _transcribe_gemini(
        self,
        file_path: str,
        language: Optional[str],
        prompt: Optional[str],
        progress_callback: Optional[Callable[[float, str], None]]
    ) -> TranscriptionResult:
        model_name = self.model or "gemini-2.5-flash"
        if progress_callback:
            progress_callback(15.0, f"Codificando áudio para Google Gemini ({model_name})...")

        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        b64_data = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Determina o mime type
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".mp3": "audio/mp3",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".m4a": "audio/m4a",
            ".flac": "audio/flac",
            ".mp4": "video/mp4",
            ".webm": "video/webm"
        }
        mime_type = mime_map.get(ext, "audio/mp3")

        lang_instruction = f" no idioma {language}" if (language and language.strip().lower() != "auto") else ""
        prompt_instruction = f" Considere o seguinte contexto ou vocabulário especializado: {prompt}." if prompt else ""
        system_instruction = (
            f"Transcreva este arquivo de áudio com alta fidelidade{lang_instruction}.{prompt_instruction} "
            "Retorne a resposta estritamente em formato JSON com o seguinte esquema: "
            "{\"language\": \"código_do_idioma_ex_pt\", \"segments\": [{\"id\": 1, \"start\": 0.0, \"end\": 3.5, \"text\": \"texto do trecho\"}]}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": system_instruction},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }

        if progress_callback:
            progress_callback(45.0, "Processando transcrição com Gemini...")

        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, json=payload)

        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(f"Erro na API Gemini ({resp.status_code}): {err_msg}")

        gemini_resp = resp.json()
        raw_text = ""
        try:
            candidates = gemini_resp.get("candidates", [])
            if candidates:
                raw_text = candidates[0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Formato inesperado na resposta do Gemini: {e}")

        # Tenta interpretar o JSON retornado
        segments_list = []
        detected_lang = language or "auto"
        total_duration = get_audio_duration(file_path)

        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                detected_lang = parsed.get("language", detected_lang)
                raw_segs = parsed.get("segments", [])
                for s in raw_segs:
                    segments_list.append(TranscriptionSegment(
                        id=int(s.get("id", len(segments_list) + 1)),
                        start=round(float(s.get("start", 0.0)), 2),
                        end=round(float(s.get("end", 0.0)), 2),
                        text=s.get("text", "").strip()
                    ))
        except Exception:
            # Fallback caso venha texto corrido
            segments_list.append(TranscriptionSegment(
                id=1,
                start=0.0,
                end=total_duration,
                text=raw_text.strip()
            ))

        full_text = " ".join([s.text for s in segments_list])
        if progress_callback:
            progress_callback(100.0, "Transcrição com Gemini finalizada!")

        return TranscriptionResult(
            text=full_text,
            segments=segments_list,
            language=detected_lang,
            duration=round(total_duration, 2),
            model=f"gemini-{model_name}",
            provider="gemini"
        )
