"""
Cliente para los endpoints PUBLICOS de la API de Kalshi (no requieren clave).
Documentacion: https://docs.kalshi.com/api-reference/market/
"""

import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
SPORTS_CATEGORIES = ("Sports", "Exotics")
TIMEOUT = 15


def get_sports_series() -> list[dict]:
    """Todas las series de las categorias deportivas."""
    series: list[dict] = []
    for category in SPORTS_CATEGORIES:
        resp = requests.get(
            f"{BASE_URL}/series", params={"category": category}, timeout=TIMEOUT
        )
        resp.raise_for_status()
        series.extend(resp.json().get("series", []))
    return series


def get_open_markets_for_series(series_ticker: str) -> list[dict]:
    """Mercados actualmente abiertos de una serie, con el titulo de su evento."""
    markets: list[dict] = []
    cursor = None
    while True:
        params = {
            "series_ticker": series_ticker,
            "status": "open",
            "with_nested_markets": "true",
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{BASE_URL}/events", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for event in data.get("events", []):
            for market in event.get("markets", []):
                markets.append(
                    {
                        "ticker": market["ticker"],
                        "event_ticker": event["event_ticker"],
                        "title": event.get("title", ""),
                        "yes_sub_title": market.get("yes_sub_title", ""),
                    }
                )
        cursor = data.get("cursor")
        if not cursor:
            break
    return markets


def get_new_trades(min_ts: int) -> list[dict]:
    """Todos los trades ejecutados en TODO Kalshi desde min_ts (se filtra por
    deporte despues, en scan.py, porque este endpoint no soporta filtrar por
    categoria)."""
    trades: list[dict] = []
    cursor = None
    while True:
        params = {"min_ts": min_ts, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{BASE_URL}/markets/trades", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        trades.extend(data.get("trades", []))
        cursor = data.get("cursor")
        if not cursor:
            break
    return trades
