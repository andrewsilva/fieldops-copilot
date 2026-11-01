from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from .services import find_stock, list_low_stock, sales_summary


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, str]
    handler: Callable[..., Any]


def build_tools(connection: sqlite3.Connection) -> dict[str, Tool]:
    return {
        "consultar_estoque": Tool(
            name="consultar_estoque",
            description="Consulta o estoque atual de um produto por nome ou SKU.",
            parameters={"query": "Nome ou SKU do produto"},
            handler=lambda query: find_stock(connection, query),
        ),
        "listar_estoque_baixo": Tool(
            name="listar_estoque_baixo",
            description="Lista produtos cuja quantidade está abaixo do mínimo.",
            parameters={},
            handler=lambda: list_low_stock(connection),
        ),
        "resumir_vendas": Tool(
            name="resumir_vendas",
            description="Soma pedidos, itens e faturamento em um período.",
            parameters={"start": "Data inicial ISO", "end": "Data final ISO"},
            handler=lambda start, end: sales_summary(
                connection, date.fromisoformat(start), date.fromisoformat(end)
            ),
        ),
    }


def describe_tools(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for tool in build_tools(connection).values()
    ]
