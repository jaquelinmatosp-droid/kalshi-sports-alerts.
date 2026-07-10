import os

import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_alert(trade: dict) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        return

    text = (
        "Movimiento grande detectado\n"
        f"{trade['market_title']}\n"
        f"Serie: {trade['series_ticker']}\n"
        f"Lado: {trade['side'].upper()}\n"
        f"{trade['count_fp']:.0f} contratos a ${trade['price_dollars']:.2f}\n"
        f"Notional: ${trade['notional_dollars']:.2f}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except requests.RequestException:
        pass
