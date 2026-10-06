"""Persistência em SQLite: palavras monitoradas, configurações por chat e ofertas já enviadas."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER NOT NULL,
    keyword    TEXT    NOT NULL,
    max_price  REAL,
    created_at INTEGER NOT NULL,
    UNIQUE (chat_id, keyword)
);

CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id      INTEGER PRIMARY KEY,
    min_discount INTEGER NOT NULL,
    paused       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sent_deals (
    chat_id    TEXT    NOT NULL,  -- id do chat ou @canal
    deal_key   TEXT    NOT NULL,
    price      REAL    NOT NULL,
    sent_at    INTEGER NOT NULL,
    PRIMARY KEY (chat_id, deal_key)
);
"""

# Reenvia uma oferta já enviada somente se o preço cair pelo menos esse percentual.
PRICE_DROP_RESEND = 0.05


@dataclass(frozen=True)
class Watch:
    id: int
    chat_id: int
    keyword: str
    max_price: float | None


class Database:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # --- watches -----------------------------------------------------------

    def add_watch(self, chat_id: int, keyword: str, max_price: float | None) -> bool:
        """Adiciona ou atualiza uma palavra-chave. Retorna True se for nova."""
        keyword = keyword.strip().lower()
        cur = self.conn.execute(
            "SELECT id FROM watches WHERE chat_id = ? AND keyword = ?", (chat_id, keyword)
        )
        exists = cur.fetchone() is not None
        self.conn.execute(
            """
            INSERT INTO watches (chat_id, keyword, max_price, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (chat_id, keyword) DO UPDATE SET max_price = excluded.max_price
            """,
            (chat_id, keyword, max_price, int(time.time())),
        )
        self.conn.commit()
        return not exists

    def remove_watch(self, chat_id: int, keyword_or_id: str) -> bool:
        if keyword_or_id.isdigit():
            cur = self.conn.execute(
                "DELETE FROM watches WHERE chat_id = ? AND id = ?", (chat_id, int(keyword_or_id))
            )
        else:
            cur = self.conn.execute(
                "DELETE FROM watches WHERE chat_id = ? AND keyword = ?",
                (chat_id, keyword_or_id.strip().lower()),
            )
        self.conn.commit()
        return cur.rowcount > 0

    def list_watches(self, chat_id: int | None = None) -> list[Watch]:
        if chat_id is None:
            rows = self.conn.execute("SELECT * FROM watches ORDER BY id").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM watches WHERE chat_id = ? ORDER BY id", (chat_id,)
            ).fetchall()
        return [Watch(r["id"], r["chat_id"], r["keyword"], r["max_price"]) for r in rows]

    # --- configurações por chat ---------------------------------------------

    def get_min_discount(self, chat_id: int, default: int) -> int:
        row = self.conn.execute(
            "SELECT min_discount FROM chat_settings WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return row["min_discount"] if row else default

    def set_min_discount(self, chat_id: int, value: int, default: int) -> None:
        self._ensure_settings(chat_id, default)
        self.conn.execute(
            "UPDATE chat_settings SET min_discount = ? WHERE chat_id = ?", (value, chat_id)
        )
        self.conn.commit()

    def is_paused(self, chat_id: int) -> bool:
        row = self.conn.execute(
            "SELECT paused FROM chat_settings WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return bool(row and row["paused"])

    def set_paused(self, chat_id: int, paused: bool, default: int) -> None:
        self._ensure_settings(chat_id, default)
        self.conn.execute(
            "UPDATE chat_settings SET paused = ? WHERE chat_id = ?", (int(paused), chat_id)
        )
        self.conn.commit()

    def _ensure_settings(self, chat_id: int, default: int) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO chat_settings (chat_id, min_discount) VALUES (?, ?)",
            (chat_id, default),
        )

    # --- ofertas enviadas ---------------------------------------------------

    def should_send(self, chat_id: int | str, deal_key: str, price: float) -> bool:
        row = self.conn.execute(
            "SELECT price FROM sent_deals WHERE chat_id = ? AND deal_key = ?",
            (str(chat_id), deal_key),
        ).fetchone()
        if row is None:
            return True
        return price <= row["price"] * (1 - PRICE_DROP_RESEND)

    def mark_sent(self, chat_id: int | str, deal_key: str, price: float) -> None:
        self.conn.execute(
            """
            INSERT INTO sent_deals (chat_id, deal_key, price, sent_at) VALUES (?, ?, ?, ?)
            ON CONFLICT (chat_id, deal_key) DO UPDATE SET price = excluded.price,
                                                          sent_at = excluded.sent_at
            """,
            (str(chat_id), deal_key, price, int(time.time())),
        )
        self.conn.commit()

    def prune_sent(self, older_than_days: int = 30) -> int:
        limit = int(time.time()) - older_than_days * 86400
        cur = self.conn.execute("DELETE FROM sent_deals WHERE sent_at < ?", (limit,))
        self.conn.commit()
        return cur.rowcount
