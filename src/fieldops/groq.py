from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


class GroqError(RuntimeError):
    """Falha ao conversar com a API do Groq."""


class GroqClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.base_url = (
            base_url or os.getenv("GROQ_URL", "https://api.groq.com/openai/v1")
        ).rstrip("/")
        self.timeout = timeout or float(os.getenv("GROQ_TIMEOUT", "30"))

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise GroqError("GROQ_API_KEY não está configurada.")

        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Você é um assistente de operações. Responda em "
                            "português do Brasil, de forma curta e objetiva. "
                            "Não invente dados."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise GroqError("Não foi possível acessar a API do Groq.") from error

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise GroqError("O Groq retornou uma resposta inválida.") from error
        if not isinstance(content, str) or not content.strip():
            raise GroqError("O Groq retornou uma resposta vazia.")
        return content.strip()
