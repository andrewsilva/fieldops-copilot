from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WhatsAppMessage:
    message_id: str
    sender_id: str
    message_type: str
    text: str | None


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
