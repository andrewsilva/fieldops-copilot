from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import Any


@dataclass(frozen=True)
class WhatsAppMessage:
    message_id: str
    sender_id: str
    message_type: str
    text: str | None


class WhatsAppError(RuntimeError):
    """Falha ao chamar a WhatsApp Cloud API."""


class WhatsAppClient:
    def __init__(
        self,
        access_token: str | None = None,
        phone_number_id: str | None = None,
        api_version: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = api_version or os.getenv("WHATSAPP_API_VERSION", "v23.0")
        self.base_url = (
            base_url or os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com")
        ).rstrip("/")
        self.timeout = timeout or float(os.getenv("WHATSAPP_TIMEOUT", "15"))

    @property
    def configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    def send_text(self, recipient: str, text: str) -> str:
        if not self.configured:
            raise WhatsAppError(
                "WHATSAPP_ACCESS_TOKEN e WHATSAPP_PHONE_NUMBER_ID são obrigatórios."
            )
        payload = json.dumps(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/{self.api_version}/{self.phone_number_id}/messages",
            data=payload,
            headers={
                "Authorization": "Bearer " + self.access_token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise WhatsAppError("Não foi possível enviar a mensagem pela Meta.") from error
        try:
            message_id = body["messages"][0]["id"]
        except (KeyError, IndexError, TypeError) as error:
            raise WhatsAppError("A Meta retornou uma resposta inválida.") from error
        if not isinstance(message_id, str) or not message_id:
            raise WhatsAppError("A Meta não retornou o identificador da mensagem.")
        return message_id


def verify_webhook(
    mode: str | None,
    token: str | None,
    challenge: str | None,
    expected_token: str | None = None,
) -> str | None:
    configured_token = expected_token or os.getenv("WHATSAPP_VERIFY_TOKEN")
    if (
        mode == "subscribe"
        and configured_token
        and token == configured_token
        and challenge
    ):
        return challenge
    return None


def parse_messages(payload: dict[str, Any]) -> list[WhatsAppMessage]:
    messages: list[WhatsAppMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                message_type = message.get("type", "unknown")
                text = None
                if message_type == "text":
                    text = message.get("text", {}).get("body")
                messages.append(
                    WhatsAppMessage(
                        message_id=message.get("id", ""),
                        sender_id=message.get("from", ""),
                        message_type=message_type,
                        text=text,
                    )
                )
    return messages
