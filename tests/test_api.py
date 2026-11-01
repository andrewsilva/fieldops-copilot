from fastapi.testclient import TestClient

from fieldops.api import app


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
