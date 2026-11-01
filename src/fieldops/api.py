from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from .db import get_connection
from .services import find_stock, list_low_stock, sales_summary

app = FastAPI(title="FieldOps Copilot", version="0.1.0")


def connection_dependency():
    yield from get_connection()


Connection = Annotated[object, Depends(connection_dependency)]


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
