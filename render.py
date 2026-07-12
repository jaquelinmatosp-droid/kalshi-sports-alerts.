from datetime import datetime, timezone


def _format_time(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return str(value)


_PHASE_LABELS = {
    "pre-partido": "Pre-partido",
    "en directo": "En directo",
    "post-partido": "Post-partido",
    "desconocido": "?",
}
_PHASE_CLASS = {
    "pre-partido": "phase-pre",
    "en directo": "phase-live",
    "post-partido": "phase-post",
    "desconocido": "phase-unknown",
}


def render_dashboard(trades: list[dict], summary: dict) -> str:
    if trades:
        rows = "".join(
            f"""<tr>
<td>{_format_time(t['created_time'])}</td>
<td>{t['market_title']}</td>
<td>{t['series_ticker']}</td>
<td class="side-{t['side']}">{t['side'].upper()}</td>
<td>{float(t['count_fp']):,.0f}</td>
<td>${float(t['price_dollars']):.2f}</td>
<td>${float(t['notional_dollars']):,.2f}</td>
<td class="{_PHASE_CLASS.get(t.get('game_phase'), 'phase-unknown')}">{_PHASE_LABELS.get(t.get('game_phase'), '?')}</td>
</tr>"""
            for t in trades
        )
    else:
        rows = (
            '<tr><td colspan="8" class="empty">'
            "Todavia no se ha detectado ningun movimiento grande."
            "</td></tr>"
        )

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="120">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kalshi Sports - Movimientos Grandes</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; background: #0f1117; color: #e6e6e6; margin: 0; padding: 24px; }}
  h1 {{ font-size: 20px; font-weight: 500; margin: 0 0 4px; }}
  p.sub {{ color: #9a9ea8; font-size: 13px; margin: 0 0 20px; }}
  .summary {{ display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }}
  .card {{ background: #171a23; border-radius: 12px; padding: 16px 20px; flex: 1; min-width: 140px; }}
  .card .label {{ font-size: 12px; color: #9a9ea8; }}
  .card .value {{ font-size: 26px; font-weight: 500; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #262a35; font-size: 13px; }}
  th {{ color: #9a9ea8; font-weight: 400; }}
  .side-yes {{ color: #6fd08c; font-weight: 500; }}
  .side-no {{ color: #e0716f; font-weight: 500; }}
  .phase-pre {{ color: #6fa8d0; }}
  .phase-live {{ color: #e0b96f; }}
  .phase-post {{ color: #9a9ea8; }}
  .phase-unknown {{ color: #6a6e78; }}
  .empty {{ color: #9a9ea8; padding: 20px 0; font-size: 13px; text-align: center; }}
</style>
</head>
<body>
<h1>Kalshi Sports - Movimientos Grandes</h1>
<p class="sub">Actualizado: {updated} (se refresca solo cada pocos minutos)</p>
<div class="summary">
  <div class="card"><div class="label">Movimientos (24h)</div><div class="value">{summary['total']}</div></div>
  <div class="card"><div class="label">Notional total</div><div class="value">${float(summary['notional']):,.0f}</div></div>
  <div class="card"><div class="label">Series activas</div><div class="value">{summary['sports']}</div></div>
</div>
<table>
<thead><tr><th>Hora</th><th>Mercado</th><th>Serie</th><th>Lado</th><th>Contratos</th><th>Precio</th><th>Notional</th><th>Fase</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>
"""
