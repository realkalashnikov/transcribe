import os
import json
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings

ACTION_SYSTEM_PROMPTS = {
    "summary": (
        "Você é um assistente executivo especializado em síntese de conteúdo. "
        "Leia a transcrição fornecida e gere um Resumo Executivo conciso, bem estruturado e objetivo. "
        "Destaque o tema central, as principais conclusões e insights em português claro (a menos que outro idioma seja solicitado)."
    ),
    "action_items": (
        "Você é um secretário executivo de alto nível. "
        "A partir da transcrição fornecida, elabore uma Ata de Reunião profissional contendo:\n"
        "1. 🎯 Objetivo / Contexto Principal\n"
        "2. 💡 Decisões Tomadas\n"
        "3. ✅ Lista de Ações e Próximos Passos (com responsáveis ou prazos identificados, se houver)\n"
        "4. ⚠️ Pontos de Atenção ou Bloqueios"
    ),
    "bullet_points": (
        "Você é um analista de conteúdo. "
        "Extraia os Principais Tópicos da transcrição em formato de tópicos (bullet points) organizados por relevância. "
        "Cada tópico deve ser direto, informativo e sem enrolação."
    ),
    "translate": (
        "Você é um tradutor profissional nativo. "
        "Traduza a transcrição a seguir para o idioma solicitado preservando o tom, contexto, jargões técnicos e nuances naturais da fala. "
        "Retorne apenas a tradução polida."
    )
}

class LLMActionService:
    """
    Serviço de Pós-Processamento e Ações Inteligentes com LLM:
    - Resumo Executivo
    - Ata de Reunião & Próximos Passos
    - Principais Tópicos (Bullet Points)
    - Tradução Contextual
    Suporta Groq (Llama 3.3), OpenAI (GPT-4o-mini), Google Gemini (Gemini 2.5 Flash) e Ollama (Local).
    """

    @staticmethod
    def process_action(
        text: str,
        action: str = "summary",
        target_language: str = "pt",
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("O texto da transcrição está vazio.")

        act = action.lower().strip()
        if act not in ACTION_SYSTEM_PROMPTS:
            raise ValueError(f"Ação desconhecida: '{action}'. Ações válidas: {list(ACTION_SYSTEM_PROMPTS.keys())}")

        system_prompt = ACTION_SYSTEM_PROMPTS[act]
        if act == "translate":
            system_prompt += f"\nIdioma de destino da tradução: {target_language}."

        user_content = f"Transcrição para análise:\n\n{text}"

        # Determina o provedor e a chave
        prov = (provider or "").lower().strip()
        if not prov:
            if api_key:
                prov = "groq"
            elif os.getenv("GROQ_API_KEY"):
                prov = "groq"
            elif os.getenv("OPENAI_API_KEY"):
                prov = "openai"
            elif os.getenv("GEMINI_API_KEY"):
                prov = "gemini"
            else:
                prov = "groq"

        key = (api_key or "").strip()
        if not key:
            if prov == "groq":
                key = os.getenv("GROQ_API_KEY", "")
            elif prov == "openai":
                key = os.getenv("OPENAI_API_KEY", "")
            elif prov == "gemini":
                key = os.getenv("GEMINI_API_KEY", "")

        if prov in ("groq", "openai", "gemini") and not key:
            raise ValueError(f"Chave de API não informada para o provedor '{prov}'. Configure nas opções da interface ou nas variáveis de ambiente.")

        if prov == "groq":
            return LLMActionService._call_groq(system_prompt, user_content, key, model)
        elif prov == "openai":
            return LLMActionService._call_openai(system_prompt, user_content, key, model)
        elif prov == "gemini":
            return LLMActionService._call_gemini(system_prompt, user_content, key, model)
        elif prov == "ollama":
            return LLMActionService._call_ollama(system_prompt, user_content, model)
        elif prov in ("custom", "openai_compatible") or (base_url and prov not in ("groq", "gemini")):
            return LLMActionService._call_custom_openai(system_prompt, user_content, base_url or "http://localhost:11434/v1", key, model)
        else:
            raise ValueError(f"Provedor LLM não suportado: {prov}")

    @staticmethod
    def _call_custom_openai(system_prompt: str, user_content: str, base_url: str, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        model_name = model or "llama-3.3-70b-versatile"
        endpoint = f"{base_url.rstrip('/')}/chat/completions" if not base_url.endswith("/chat/completions") else base_url
        headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3
        }

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(endpoint, json=payload, headers=headers)

        if resp.status_code != 200:
            raise RuntimeError(f"Erro no endpoint personalizado ({resp.status_code}): {resp.text}")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Provedor personalizado não retornou texto na resposta.")

        content = choices[0].get("message", {}).get("content", "").strip()
        return {
            "result": content,
            "provider": "custom",
            "model": model_name,
            "usage": data.get("usage", {})
        }

    @staticmethod
    def _call_groq(system_prompt: str, user_content: str, api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
        model_name = model or "llama-3.3-70b-versatile"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Erro na API Groq ({resp.status_code}): {resp.text}")
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return {
                "result": content,
                "provider": "groq",
                "model": model_name,
                "usage": data.get("usage", {})
            }

    @staticmethod
    def _call_openai(system_prompt: str, user_content: str, api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
        model_name = model or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Erro na API OpenAI ({resp.status_code}): {resp.text}")
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return {
                "result": content,
                "provider": "openai",
                "model": model_name,
                "usage": data.get("usage", {})
            }

    @staticmethod
    def _call_gemini(system_prompt: str, user_content: str, api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
        model_name = model or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Erro na API Gemini ({resp.status_code}): {resp.text}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates or "content" not in candidates[0]:
                raise ValueError("A API Gemini não retornou nenhum texto.")
            content = candidates[0]["content"]["parts"][0]["text"].strip()
            return {
                "result": content,
                "provider": "gemini",
                "model": model_name,
                "usage": data.get("usageMetadata", {})
            }

    @staticmethod
    def _call_ollama(system_prompt: str, user_content: str, model: Optional[str] = None) -> Dict[str, Any]:
        model_name = model or "llama3.2"
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3
        }
        with httpx.Client(timeout=180.0) as client:
            try:
                resp = client.post(url, json=payload)
            except Exception as e:
                raise ValueError(f"Não foi possível conectar ao servidor Ollama em '{url}': {e}. Certifique-se de que o Ollama está em execução.")
            if resp.status_code != 200:
                raise ValueError(f"Erro no Ollama ({resp.status_code}): {resp.text}")
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return {
                "result": content,
                "provider": "ollama",
                "model": model_name
            }
