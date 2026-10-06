"""Interface comum para todas as fontes de ofertas (marketplaces)."""

from __future__ import annotations

import abc
import re

import httpx

from promobot.models import Deal

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 promobot/1.0"
)


class Source(abc.ABC):
    """Uma fonte de ofertas. Cada marketplace implementa `search`."""

    #: identificador curto, usado no banco e nos comandos
    name: str = ""
    #: nome exibido nas mensagens
    label: str = ""

    def __init__(self, client: httpx.AsyncClient, max_results: int = 20):
        self.client = client
        self.max_results = max_results

    @abc.abstractmethod
    async def search(self, keyword: str) -> list[Deal]:
        """Busca ofertas para a palavra-chave."""


_BRL_RE = re.compile(r"R\$\s*([\d.]+(?:,\d{1,2})?)")


def parse_brl(text: str) -> list[float]:
    """Extrai valores em reais de um texto: 'De R$ 1.299,90 por R$ 999' -> [1299.9, 999.0]."""
    values = []
    for match in _BRL_RE.findall(text):
        try:
            values.append(float(match.replace(".", "").replace(",", ".")))
        except ValueError:
            continue
    return values


def to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
