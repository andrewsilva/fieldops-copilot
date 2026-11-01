from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    minimum_stock INTEGER NOT NULL CHECK (minimum_stock >= 0),
    current_stock INTEGER NOT NULL CHECK (current_stock >= 0)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    sold_at TEXT NOT NULL
);
"""

SEED = """
INSERT OR IGNORE INTO products (id, sku, name, minimum_stock, current_stock)
VALUES
    (1, 'CAM-001', 'Câmera de segurança', 10, 4),
    (2, 'CAB-002', 'Cabo de rede 10m', 20, 35),
    (3, 'MOU-003', 'Mouse sem fio', 8, 3);

INSERT OR IGNORE INTO sales (id, product_id, quantity, total_cents, sold_at)
VALUES
    (1, 1, 2, 30000, '2026-10-31T09:30:00'),
    (2, 2, 5, 12500, '2026-10-31T14:15:00'),
    (3, 3, 1, 7990, '2026-10-30T16:00:00');
"""


def connect(database: str | Path = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(database, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    connection.executescript(SEED)
    return connection


def get_connection() -> Iterator[sqlite3.Connection]:
    with closing(connect()) as connection:
        yield connection
