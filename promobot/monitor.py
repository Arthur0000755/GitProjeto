"""Busca em todas as fontes ao mesmo tempo e filtra as ofertas relevantes."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from promobot.models import Deal
from promobot.sources import Source

log = logging.getLogger(__name__)


@dataclass
class SearchResult:
    deals: list[Deal] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)  # label da fonte -> erro


async def search_all(sources: list[Source], keyword: str) -> SearchResult:
    """Consulta todas as fontes em paralelo; falhas de uma fonte não afetam as demais."""

    async def run(source: Source) -> list[Deal]:
        return await source.search(keyword)

    result = SearchResult()
    outcomes = await asyncio.gather(*(run(s) for s in sources), return_exceptions=True)
    for source, outcome in zip(sources, outcomes):
        if isinstance(outcome, BaseException):
            log.warning("Erro na fonte %s ao buscar %r: %s", source.label, keyword, outcome)
            result.errors[source.label] = str(outcome) or outcome.__class__.__name__
        else:
            result.deals.extend(outcome)
    return result


def filter_deals(
    deals: list[Deal],
    keyword: str,
    min_discount: float = 0,
    max_price: float | None = None,
) -> list[Deal]:
    """Mantém só ofertas que batem com a busca, desconto mínimo e preço máximo.

    Ordena pelo maior desconto e remove duplicatas.
    """
    words = keyword.lower().split()
    seen: set[str] = set()
    selected = []
    for deal in deals:
        if deal.key in seen:
            continue
        seen.add(deal.key)
        if not all(w in deal.title.lower() for w in words):
            continue
        if deal.discount_pct < min_discount:
            continue
        if max_price is not None and deal.price > max_price:
            continue
        selected.append(deal)
    selected.sort(key=lambda d: (-d.discount_pct, d.price))
    return selected
