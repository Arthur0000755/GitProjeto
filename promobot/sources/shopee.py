"""Shopee — Open API de afiliados (GraphQL).

Requer cadastro no programa de afiliados: https://affiliate.shopee.com.br
(menu "Open API" para gerar AppID e Secret). Os links retornados já são de afiliado.
"""

from __future__ import annotations

import hashlib
import json
import time

import httpx

from promobot.models import Deal
from promobot.sources.base import Source, to_float

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

QUERY = """
query ($keyword: String, $limit: Int) {
  productOfferV2(keyword: $keyword, sortType: 2, page: 1, limit: $limit) {
    nodes {
      itemId
      productName
      priceMin
      priceDiscountRate
      imageUrl
      offerLink
      productLink
      shopName
    }
  }
}
"""


class ShopeeSource(Source):
    name = "shopee"
    label = "Shopee"

    def __init__(self, client: httpx.AsyncClient, app_id: str, secret: str, max_results: int = 20):
        super().__init__(client, max_results)
        self.app_id = app_id
        self.secret = secret

    def _auth_header(self, payload: str, timestamp: int) -> str:
        signature = hashlib.sha256(
            f"{self.app_id}{timestamp}{payload}{self.secret}".encode()
        ).hexdigest()
        return f"SHA256 Credential={self.app_id}, Timestamp={timestamp}, Signature={signature}"

    async def search(self, keyword: str) -> list[Deal]:
        payload = json.dumps(
            {"query": QUERY, "variables": {"keyword": keyword, "limit": self.max_results}},
            separators=(",", ":"),
        )
        resp = await self.client.post(
            ENDPOINT,
            content=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": self._auth_header(payload, int(time.time())),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            raise RuntimeError(f"Shopee API: {data['errors'][0].get('message')}")
        return self.parse(data)

    def parse(self, data: dict) -> list[Deal]:
        nodes = (((data.get("data") or {}).get("productOfferV2") or {}).get("nodes")) or []
        deals = []
        for node in nodes:
            price = to_float(node.get("priceMin"))
            url = node.get("offerLink") or node.get("productLink")
            if price is None or not url:
                continue
            rate = to_float(node.get("priceDiscountRate")) or 0
            original = round(price / (1 - rate / 100), 2) if 0 < rate < 100 else None
            deals.append(
                Deal(
                    source=self.name,
                    item_id=str(node.get("itemId")),
                    title=node.get("productName", ""),
                    url=url,
                    price=price,
                    original_price=original,
                    image_url=node.get("imageUrl"),
                    store=node.get("shopName"),
                )
            )
        return deals
