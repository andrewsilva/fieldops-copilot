from fastapi.testclient import TestClient

from datetime import date

from fieldops.agent import OperationsAgent
from fieldops.api import app
from fieldops.db import connect
from fieldops.groq import GroqClient, GroqError
from fieldops.whatsapp import WhatsAppClient, WhatsAppError


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_stock_search_returns_matching_products():
    response = client.get("/tools/stock", params={"query": "câmera"})

    assert response.status_code == 200
    assert response.json()["items"][0]["sku"] == "CAM-001"
    assert response.json()["items"][0]["below_minimum"] is True


def test_low_stock_lists_only_products_below_minimum():
    response = client.get("/tools/low-stock")

    assert response.status_code == 200
    assert [item["sku"] for item in response.json()["items"]] == ["CAM-001", "MOU-003"]


def test_sales_summary_aggregates_date_range():
    response = client.get(
        "/tools/sales-summary",
        params={"start": "2026-10-31", "end": "2026-10-31"},
    )

    assert response.status_code == 200
    assert response.json()["order_count"] == 2
    assert response.json()["item_count"] == 7
    assert response.json()["total_cents"] == 42500


def test_sales_summary_rejects_reversed_range():
    response = client.get(
        "/tools/sales-summary",
        params={"start": "2026-11-01", "end": "2026-10-31"},
    )

    assert response.status_code == 400


def test_agent_routes_low_stock_question_to_typed_tool():
    agent = OperationsAgent(connect(), today=date(2026, 10, 31))

    result = agent.answer("Quais produtos estão com baixo estoque?")

    assert result.tool_name == "listar_estoque_baixo"
    assert "2 produto(s)" in result.message
    assert result.data[0]["sku"] == "CAM-001"


def test_chat_routes_sales_question_and_returns_audit_data():
    response = client.post(
        "/chat",
        json={"message": "Quanto vendemos de 2026-10-31 a 2026-10-31?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool"] == "resumir_vendas"
    assert body["arguments"] == {
        "start": "2026-10-31",
        "end": "2026-10-31",
    }
    assert "R$ 425,00" in body["message"]


def test_agent_rejects_unknown_request_without_calling_a_tool():
    agent = OperationsAgent(connect(), today=date(2026, 10, 31))

    result = agent.answer("Me conte uma piada")

    assert result.tool_name is None
    assert "Ainda não consigo" in result.message


def test_agent_can_use_a_local_model_to_rephrase_tool_result():
    class FakeModel:
        def generate(self, prompt: str) -> str:
            assert "listar_estoque_baixo" in prompt
            return "Atenção: há produtos que precisam de reposição."

    agent = OperationsAgent(
        connect(), today=date(2026, 10, 31), language_model=FakeModel()
    )

    result = agent.answer("Quais produtos estão com baixo estoque?")

    assert result.message == "Atenção: há produtos que precisam de reposição."
    assert result.tool_name == "listar_estoque_baixo"


def test_groq_client_parses_chat_response(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":" resposta online "}}]}'

    monkeypatch.setattr("fieldops.groq.urlopen", lambda *args, **kwargs: FakeResponse())

    assert GroqClient(api_key="test-key", timeout=1).generate("oi") == "resposta online"


def test_groq_client_requires_api_key():
    try:
        GroqClient(api_key="").generate("oi")
    except GroqError as error:
        assert "GROQ_API_KEY" in str(error)
    else:
        raise AssertionError("A chamada deveria exigir uma chave do Groq")


def test_whatsapp_webhook_returns_meta_challenge(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "fieldops-dev")

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "fieldops-dev",
            "hub.challenge": "12345",
        },
    )

    assert response.status_code == 200
    assert response.text == "12345"


def test_whatsapp_webhook_routes_text_to_agent():
    response = client.post(
        "/webhooks/whatsapp",
        json={
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.test",
                                        "from": "5511999999999",
                                        "type": "text",
                                        "text": {
                                            "body": "Quais produtos estão com baixo estoque?"
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["received"] == 1
    assert body["replies"][0]["sender_id"] == "5511999999999"
    assert body["replies"][0]["tool"] == "listar_estoque_baixo"


def test_whatsapp_webhook_acknowledges_non_text_message():
    response = client.post(
        "/webhooks/whatsapp",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.audio",
                                        "from": "5511999999999",
                                        "type": "audio",
                                        "audio": {"id": "media-id"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert response.status_code == 200
    assert "Áudio entra" in response.json()["replies"][0]["message"]


def test_whatsapp_client_posts_text_and_returns_meta_message_id(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"messages":[{"id":"wamid.response"}]}'

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["body"] = request.data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("fieldops.whatsapp.urlopen", fake_urlopen)

    client = WhatsAppClient(
        access_token="secret-token",
        phone_number_id="123456",
        api_version="v23.0",
    )

    assert client.send_text("5511999999999", "Olá") == "wamid.response"
    assert captured["url"].endswith("/v23.0/123456/messages")
    assert captured["authorization"] == "Bearer secret-token"
    assert b'"to": "5511999999999"' in captured["body"]


def test_whatsapp_client_requires_credentials():
    client = WhatsAppClient(access_token="", phone_number_id="")

    try:
        client.send_text("5511999999999", "Olá")
    except WhatsAppError as error:
        assert "WHATSAPP_ACCESS_TOKEN" in str(error)
    else:
        raise AssertionError("A chamada deveria exigir as credenciais da Meta")


def test_whatsapp_webhook_sends_reply_when_meta_is_configured(monkeypatch):
    sent = {}

    def fake_send(self, recipient, text):
        sent["recipient"] = recipient
        sent["text"] = text
        return "wamid.sent"

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone-id")
    monkeypatch.setattr(WhatsAppClient, "send_text", fake_send)

    response = client.post(
        "/webhooks/whatsapp",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.incoming",
                                        "from": "5511999999999",
                                        "type": "text",
                                        "text": {
                                            "body": "Quais produtos estão com baixo estoque?"
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["replies"][0]["sent_message_id"] == "wamid.sent"
    assert sent["recipient"] == "5511999999999"
