import logging
import os
import time
from datetime import datetime, timedelta

from db import ensure_table, get_recent_large_trades, get_today_summary, insert_large_trade
from kalshi_api import get_new_trades, get_open_markets_for_series, get_sports_series
from notify import send_telegram_alert
from render import render_dashboard

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("scan")

THRESHOLD_USD = float(os.environ.get("LARGE_TRADE_THRESHOLD_USD", "1000"))
LOOKBACK_SECONDS = int(os.environ.get("LOOKBACK_SECONDS", "1200"))
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "docs/index.html")

# Duracion tipica por deporte, para estimar cuando empezo el partido a
# partir de expected_expiration_time. Es una aproximacion, no un dato
# oficial de Kalshi (no exponen la hora de inicio real en los datos basicos
# de mercado).
SPORT_DURATION_HOURS = {
    "ATP": 3.0,
    "WTA": 2.5,
    "ITF": 2.5,
    "TENNIS": 3.0,
    "NFL": 3.5,
    "NCAAF": 3.5,
    "NBA": 2.5,
    "NCAAB": 2.5,
    "MLB": 3.0,
    "NHL": 2.75,
    "SOCCER": 2.0,
    "MLS": 2.0,
    "EPL": 2.0,
    "LALIGA": 2.0,
    "LOL": 1.0,
    "ESPORT": 1.0,
    "GOLF": 5.0,
    "MMA": 3.0,
    "UFC": 3.0,
}
DEFAULT_DURATION_HOURS = 2.5


def parse_kalshi_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def estimate_duration_hours(series_ticker: str) -> float:
    upper = series_ticker.upper()
    for keyword, hours in SPORT_DURATION_HOURS.items():
        if keyword in upper:
            return hours
    return DEFAULT_DURATION_HOURS


def classify_game_phase(
    series_ticker: str, expected_expiration: "datetime | None", trade_time: datetime
) -> str:
    """Estimacion aproximada, no un dato oficial de Kalshi."""
    if expected_expiration is None:
        return "desconocido"
    duration = estimate_duration_hours(series_ticker)
    estimated_start = expected_expiration - timedelta(hours=duration)
    if trade_time < estimated_start:
        return "pre-partido"
    if trade_time <= expected_expiration:
        return "en directo"
    return "post-partido"


def trade_notional(trade: dict) -> tuple[str, float, float]:
    side = trade.get("taker_side", "yes")
    price = (
        float(trade["yes_price_dollars"])
        if side == "yes"
        else float(trade["no_price_dollars"])
    )
    count = float(trade["count_fp"])
    return side, price, round(count * price, 2)


def build_tracked_markets() -> dict[str, dict]:
    tracked: dict[str, dict] = {}
    for series in get_sports_series():
        series_ticker = series["ticker"]
        try:
            markets = get_open_markets_for_series(series_ticker)
        except Exception:
            logger.exception("Error obteniendo mercados de la serie %s", series_ticker)
            continue
        for m in markets:
            title = f'{m["title"]} - {m["yes_sub_title"]}'.strip(" -")
            expiration_raw = m.get("expected_expiration_time")
            expected_expiration = (
                parse_kalshi_time(expiration_raw) if expiration_raw else None
            )
            tracked[m["ticker"]] = {
                "event_ticker": m["event_ticker"],
                "series_ticker": series_ticker,
                "market_title": title,
                "expected_expiration": expected_expiration,
            }
    return tracked


def main() -> None:
    ensure_table()

    tracked_markets = build_tracked_markets()
    logger.info("Mercados deportivos abiertos ahora mismo: %d", len(tracked_markets))

    min_ts = int(time.time()) - LOOKBACK_SECONDS
    trades = get_new_trades(min_ts)
    logger.info("Trades revisados en toda la exchange: %d", len(trades))

    new_alerts: list[dict] = []
    for trade in trades:
        meta = tracked_markets.get(trade["ticker"])
        if not meta:
            continue

        side, price, notional = trade_notional(trade)
        if notional < THRESHOLD_USD:
            continue

        created_time = parse_kalshi_time(trade["created_time"])
        game_phase = classify_game_phase(
            meta["series_ticker"], meta.get("expected_expiration"), created_time
        )

        record = {
            "trade_id": trade["trade_id"],
            "ticker": trade["ticker"],
            "event_ticker": meta["event_ticker"],
            "series_ticker": meta["series_ticker"],
            "market_title": meta["market_title"],
            "side": side,
            "count_fp": float(trade["count_fp"]),
            "price_dollars": price,
            "notional_dollars": notional,
            "taker_side": trade.get("taker_side"),
            "taker_book_side": trade.get("taker_book_side"),
            "created_time": created_time,
            "game_phase": game_phase,
        }
        was_new = insert_large_trade(record)
        if was_new:
            new_alerts.append(record)
            logger.info(
                "NUEVO movimiento grande: %s | %s | %.0f contratos a $%.2f | notional $%.2f | %s",
                record["market_title"],
                side.upper(),
                record["count_fp"],
                price,
                notional,
                game_phase,
            )

    for record in new_alerts:
        send_telegram_alert(record)

    recent = get_recent_large_trades(limit=100)
    summary = get_today_summary()
    html = render_dashboard(recent, summary)

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("Dashboard escrito en %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()
