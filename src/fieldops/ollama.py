from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    """Falha ao conversar com o servidor Ollama local."""


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.timeout = timeout or float(os.getenv("OLLAMA_TIMEOUT", "30"))

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise OllamaError(
                f"Não foi possível acessar o Ollama em {self.base_url}."
            ) from error
        if not isinstance(body.get("response"), str):
            raise OllamaError("O Ollama retornou uma resposta inválida.")
        return body["response"].strip()
