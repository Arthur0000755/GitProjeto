"""AliExpress — API de afiliados (aliexpress.affiliate.product.query).

Requer cadastro em https://portals.aliexpress.com e criação de um app em
https://openservice.aliexpress.com para obter App Key / App Secret.
"""

from __future__ import annotations

import hashlib
import hmac
import time

import httpx

from promobot.models import Deal
from promobot.sources.base import Source, to_float

ENDPOINT = "https://api-sg.aliexpress.com/sync"
METHOD = "aliexpress.affiliate.product.query"


def sign_params(params: dict[str, str], secret: str) -> str:
    base = "".join(f"{k}{params[k]}" for k in sorted(params))
    return hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest().upper()


class AliExpressSource(Source):
    name = "aliexpress"
    label = "AliExpress"

    def __init__(
        self,
        client: httpx.AsyncClient,
        app_key: str,
        app_secret: str,
        tracking_id: str | None = None,
        max_results: int = 20,
    ):
        super().__init__(client, max_results)
        self.app_key = app_key
        self.app_secret = app_secret
        self.tracking_id = tracking_id

    async def search(self, keyword: str) -> list[Deal]:
        params = {
            "method": METHOD,
            "app_key": self.app_key,
            "sign_method": "sha256",
            "timestamp": str(int(time.time() * 1000)),
            "keywords": keyword,
            "page_size": str(self.max_results),
            "sort": "SALE_PRICE_ASC",
            "target_currency": "BRL",
            "target_language": "PT",
            "ship_to_country": "BR",
        }
        if self.tracking_id:
            params["tracking_id"] = self.tracking_id
        params["sign"] = sign_params(params, self.app_secret)
        resp = await self.client.post(ENDPOINT, data=params)
        resp.raise_for_status()
        data = resp.json()
        if "error_response" in data:
            raise RuntimeError(f"AliExpress API: {data['error_response'].get('msg')}")
        return self.parse(data)

    def parse(self, data: dict) -> list[Deal]:
        resp = (data.get("aliexpress_affiliate_product_query_response") or {}).get(
            "resp_result"
        ) or {}
        products = ((resp.get("result") or {}).get("products") or {}).get("product") or []
        deals = []
        for p in products:
            price = to_float(p.get("target_sale_price") or p.get("sale_price"))
            url = p.get("promotion_link") or p.get("product_detail_url")
            if price is None or not url:
                continue
            deals.append(
                Deal(
                    source=self.name,
                    item_id=str(p.get("product_id")),
                    title=p.get("product_title", ""),
                    url=url,
                    price=price,
                    original_price=to_float(
                        p.get("target_original_price") or p.get("original_price")
                    ),
                    currency=p.get("target_sale_price_currency", "BRL"),
                    image_url=p.get("product_main_image_url"),
                    store=p.get("shop_name"),
                )
            )
        return deals
