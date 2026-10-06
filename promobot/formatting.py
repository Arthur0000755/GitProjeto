"""Formatação das mensagens enviadas ao Telegram (HTML)."""

from __future__ import annotations

from html import escape

from promobot.models import Deal

SOURCE_LABELS = {
    "mercadolivre": "🟡 Mercado Livre",
    "shopee": "🟠 Shopee",
    "amazon": "📦 Amazon",
    "aliexpress": "🔴 AliExpress",
    "rss": "📰",
}


def brl(value: float) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def format_deal(deal: Deal, keyword: str | None = None) -> str:
    source = SOURCE_LABELS.get(deal.source, deal.source)
    if deal.source == "rss" and deal.store:
        source = f"{source} {deal.store}"

    title = deal.title if len(deal.title) <= 200 else deal.title[:197] + "..."
    lines = [f"🔥 <b>{escape(title)}</b>", ""]
    if deal.discount_pct > 0 and deal.original_price:
        lines.append(f"De <s>{brl(deal.original_price)}</s>")
        lines.append(f"💰 Por <b>{brl(deal.price)}</b>  (<b>-{deal.discount_pct:.0f}%</b>)")
    else:
        lines.append(f"💰 <b>{brl(deal.price)}</b>")
    lines.append("")
    store = f" · {escape(deal.store)}" if deal.store and deal.source != "rss" else ""
    lines.append(f"🏪 {escape(source)}{store}")
    if keyword:
        lines.append(f"🔎 Alerta: <i>{escape(keyword)}</i>")
    lines.append(f'🔗 <a href="{escape(deal.url, quote=True)}">Ver oferta</a>')
    return "\n".join(lines)


def format_deal_short(deal: Deal) -> str:
    """Linha compacta para listas de resultados (/buscar)."""
    source = SOURCE_LABELS.get(deal.source, deal.source)
    title = deal.title if len(deal.title) <= 80 else deal.title[:77] + "..."
    discount = f" <b>-{deal.discount_pct:.0f}%</b>" if deal.discount_pct > 0 else ""
    return (
        f'• <a href="{escape(deal.url, quote=True)}">{escape(title)}</a>\n'
        f"   {brl(deal.price)}{discount} · {escape(source)}"
    )
