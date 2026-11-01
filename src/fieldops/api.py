from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from .agent import OperationsAgent
from .db import get_connection
from .groq import GroqClient, GroqError
from .services import find_stock, list_low_stock, sales_summary
from .whatsapp import parse_messages, verify_webhook

app = FastAPI(title="FieldOps Copilot", version="0.1.0")


def connection_dependency():
    yield from get_connection()


Connection = Annotated[object, Depends(connection_dependency)]


class ChatRequest(BaseModel):
    message: str
    use_groq: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools/stock")
def stock(query: Annotated[str, Query(min_length=1)], connection: Connection):
    results = find_stock(connection, query)
    if not results:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return {"items": results}


@app.get("/tools/low-stock")
def low_stock(connection: Connection):
    return {"items": list_low_stock(connection)}


@app.get("/tools/sales-summary")
def summary(
    connection: Connection,
    start: date,
    end: date,
):
    if end < start:
        raise HTTPException(
            status_code=400, detail="A data final deve ser maior ou igual à inicial"
        )
    return sales_summary(connection, start, end)


@app.post("/chat")
def chat(request: ChatRequest, connection: Connection):
    language_model = GroqClient() if request.use_groq else None
    try:
        result = OperationsAgent(
            connection, language_model=language_model
        ).answer(request.message)
    except GroqError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "message": result.message,
        "tool": result.tool_name,
        "arguments": result.tool_arguments,
        "data": result.data,
    }


@app.get("/webhooks/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
):
    challenge = verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge is None:
        raise HTTPException(status_code=403, detail="Verificação do webhook recusada")
    return int(challenge) if challenge.isdigit() else challenge


@app.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(request: Request, connection: Connection):
    payload = await request.json()
    messages = parse_messages(payload)
    replies = []
    for message in messages:
        if message.message_type != "text" or not message.text:
            replies.append(
                {
                    "message_id": message.message_id,
                    "sender_id": message.sender_id,
                    "message": (
                        "Por enquanto consigo processar mensagens de texto. "
                        "Áudio entra na próxima etapa."
                    ),
                }
            )
            continue
        result = OperationsAgent(connection).answer(message.text)
        replies.append(
            {
                "message_id": message.message_id,
                "sender_id": message.sender_id,
                "message": result.message,
                "tool": result.tool_name,
                "arguments": result.tool_arguments,
            }
        )
    return {"received": len(messages), "replies": replies}
