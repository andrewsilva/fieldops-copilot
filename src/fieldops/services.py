from __future__ import annotations

import sqlite3
from datetime import date


def find_stock(connection: sqlite3.Connection, query: str) -> list[dict]:
    pattern = f"%{query.strip()}%"
    rows = connection.execute(
        """
        SELECT sku, name, current_stock, minimum_stock,
               current_stock < minimum_stock AS below_minimum
        FROM products
        WHERE sku LIKE ? OR name LIKE ?
        ORDER BY name
        """,
        (pattern, pattern),
    ).fetchall()
    return [
        {
            **dict(row),
            "below_minimum": bool(row["below_minimum"]),
        }
        for row in rows
    ]


def list_low_stock(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT sku, name, current_stock, minimum_stock,
               minimum_stock - current_stock AS missing_quantity
        FROM products
        WHERE current_stock < minimum_stock
        ORDER BY missing_quantity DESC, name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def sales_summary(
    connection: sqlite3.Connection, start: date, end: date
) -> dict:
    row = connection.execute(
        """
        SELECT COUNT(*) AS order_count,
               COALESCE(SUM(quantity), 0) AS item_count,
               COALESCE(SUM(total_cents), 0) AS total_cents
        FROM sales
        WHERE date(sold_at) BETWEEN date(?) AND date(?)
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "order_count": row["order_count"],
        "item_count": row["item_count"],
        "total_cents": row["total_cents"],
    }
