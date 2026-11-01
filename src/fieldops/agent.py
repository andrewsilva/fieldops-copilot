from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import date
from dataclasses import dataclass

from .tools import Tool, build_tools


@dataclass(frozen=True)
class AgentResult:
    message: str
    tool_name: str | None = None
    tool_arguments: dict[str, str] | None = None
    data: object | None = None


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _format_money(total_cents: int) -> str:
    return f"R$ {total_cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_stock(items: list[dict]) -> str:
    lines = [
        f"- {item['name']} ({item['sku']}): {item['current_stock']} unidades"
        f" (mínimo {item['minimum_stock']})"
        for item in items
    ]
    return "\n".join(lines)


class OperationsAgent:
    def __init__(
        self,
        connection: sqlite3.Connection,
        today: date | None = None,
    ) -> None:
        self.tools = build_tools(connection)
        self.today = today or date.today()

    def answer(self, text: str) -> AgentResult:
        normalized = _normalize(text)
        if not text.strip():
            return AgentResult("Mande uma pergunta sobre estoque ou vendas.")

        if "baixo estoque" in normalized or "estoque minimo" in normalized:
            return self._run(
                self.tools["listar_estoque_baixo"],
                {},
                self._low_stock_message,
            )

        if "vend" in normalized or "faturamento" in normalized:
            start, end = self._extract_period(normalized)
            arguments = {"start": start.isoformat(), "end": end.isoformat()}
            return self._run(
                self.tools["resumir_vendas"],
                arguments,
                lambda data: (
                    f"Vendas de {start.isoformat()} a {end.isoformat()}: "
                    f"{data['order_count']} pedidos, {data['item_count']} itens, "
                    f"{_format_money(data['total_cents'])}."
                ),
            )

        if "estoque" in normalized or "produto" in normalized:
            query = self._extract_product(text, normalized)
            if not query:
                return AgentResult(
                    "Posso consultar o estoque. Diga o nome ou SKU do produto."
                )
            return self._run(
                self.tools["consultar_estoque"],
                {"query": query},
                self._stock_message,
            )

        return AgentResult(
            "Ainda não consigo responder isso. Posso consultar estoque, "
            "itens abaixo do mínimo e resumo de vendas."
        )

    def _run(
        self,
        tool: Tool,
        arguments: dict[str, str],
        formatter,
    ) -> AgentResult:
        data = tool.handler(**arguments)
        return AgentResult(
            message=formatter(data),
            tool_name=tool.name,
            tool_arguments=arguments,
            data=data,
        )

    @staticmethod
    def _low_stock_message(items: list[dict]) -> str:
        if not items:
            return "Nenhum produto está abaixo do estoque mínimo."
        return f"Encontrei {len(items)} produto(s) abaixo do mínimo:\n{_format_stock(items)}"

    @staticmethod
    def _stock_message(items: list[dict]) -> str:
        if not items:
            return "Não encontrei esse produto no estoque."
        return f"Encontrei {len(items)} produto(s):\n{_format_stock(items)}"

    def _extract_period(self, text: str) -> tuple[date, date]:
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if len(dates) >= 2:
            return date.fromisoformat(dates[0]), date.fromisoformat(dates[1])
        if len(dates) == 1:
            parsed = date.fromisoformat(dates[0])
            return parsed, parsed
        return self.today, self.today

    @staticmethod
    def _extract_product(original: str, normalized: str) -> str:
        match = re.search(
            r"(?:estoque|produto)\s+(?:de|do|da|dos|das)?\s*(.+?)(?:\?|$)",
            normalized,
        )
        if not match:
            return ""
        start = match.start(1)
        return original[start:].strip().rstrip("?.")
