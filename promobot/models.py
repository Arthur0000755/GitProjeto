"""Modelos de dados compartilhados entre as fontes e o bot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Deal:
    """Uma oferta encontrada em algum marketplace."""

    source: str  # identificador da fonte, ex.: "mercadolivre"
    item_id: str  # id do produto dentro da fonte
    title: str
    url: str
    price: float
    original_price: float | None = None
    currency: str = "BRL"
    image_url: str | None = None
    store: str | None = None  # nome da loja/vendedor, quando disponível

    @property
    def key(self) -> str:
        return f"{self.source}:{self.item_id}"

    @property
    def discount_pct(self) -> float:
        """Percentual de desconto em relação ao preço original (0 se desconhecido)."""
        if not self.original_price or self.original_price <= self.price:
            return 0.0
        return round((1 - self.price / self.original_price) * 100, 1)
