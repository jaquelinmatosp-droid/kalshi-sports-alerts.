import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS large_trades (
    trade_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    event_ticker TEXT,
    series_ticker TEXT,
    market_title TEXT,
    side TEXT,
    count_fp NUMERIC,
    price_dollars NUMERIC,
    notional_dollars NUMERIC,
    taker_side TEXT,
    taker_book_side TEXT,
    created_time TIMESTAMPTZ,
    detected_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_large_trades_detected_at
    ON large_trades (detected_at DESC);
ALTER TABLE large_trades ADD COLUMN IF NOT EXISTS game_phase TEXT;
"""


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def ensure_table() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()


def insert_large_trade(trade: dict) -> bool:
    """Inserta un movimiento grande. Devuelve True si era nuevo (no estaba
    guardado ya de una pasada anterior)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO large_trades (
                    trade_id, ticker, event_ticker, series_ticker, market_title,
                    side, count_fp, price_dollars, notional_dollars,
                    taker_side, taker_book_side, created_time, game_phase
                ) VALUES (%(trade_id)s, %(ticker)s, %(event_ticker)s, %(series_ticker)s,
                          %(market_title)s, %(side)s, %(count_fp)s, %(price_dollars)s,
                          %(notional_dollars)s, %(taker_side)s, %(taker_book_side)s,
                          %(created_time)s, %(game_phase)s)
                ON CONFLICT (trade_id) DO NOTHING
                RETURNING trade_id
                """,
                trade,
            )
            was_new = cur.fetchone() is not None
        conn.commit()
    return was_new


def get_recent_large_trades(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM large_trades ORDER BY detected_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_today_summary() -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(notional_dollars), 0) AS notional,
                    COUNT(DISTINCT series_ticker) AS sports
                FROM large_trades
                WHERE detected_at >= now() - interval '24 hours'
                """
            )
            return dict(cur.fetchone())
