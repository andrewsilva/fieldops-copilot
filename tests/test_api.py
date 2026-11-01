from fastapi.testclient import TestClient

from datetime import date

from fieldops.agent import OperationsAgent
from fieldops.api import app
from fieldops.db import connect
from fieldops.ollama import OllamaClient


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


def test_ollama_client_parses_generate_response(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"response":" resposta local "}'

    monkeypatch.setattr("fieldops.ollama.urlopen", lambda *args, **kwargs: FakeResponse())

    assert OllamaClient(timeout=1).generate("oi") == "resposta local"
