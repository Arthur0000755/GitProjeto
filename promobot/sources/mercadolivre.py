"""Mercado Livre — API pública de busca (api.mercadolibre.com)."""

from __future__ import annotations

import logging
import time

import httpx

from promobot.models import Deal
from promobot.sources.base import Source, to_float

log = logging.getLogger(__name__)

API = "https://api.mercadolibre.com"


class MercadoLivreSource(Source):
    name = "mercadolivre"
    label = "Mercado Livre"

    def __init__(
        self,
        client: httpx.AsyncClient,
        max_results: int = 20,
        site: str = "MLB",
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
    ):
        super().__init__(client, max_results)
        self.site = site
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = access_token
        self._token_expires = float("inf") if access_token else 0.0

    async def _get_token(self) -> str | None:
        """Obtém um token via client_credentials, se houver credenciais configuradas.

        A API de busca do Mercado Livre pode exigir autenticação; sem credenciais
        a requisição é feita anonimamente.
        """
        if self._token and time.time() < self._token_expires:
            return self._token
        if not (self.client_id and self.client_secret):
            return None
        resp = await self.client.post(
            f"{API}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + int(data.get("expires_in", 21600)) - 60
        return self._token

    async def search(self, keyword: str) -> list[Deal]:
        headers = {}
        token = await self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = await self.client.get(
            f"{API}/sites/{self.site}/search",
            params={"q": keyword, "limit": min(self.max_results, 50)},
            headers=headers,
        )
        if resp.status_code in (401, 403) and not token:
            raise RuntimeError(
                f"HTTP {resp.status_code}: a API exige autenticação — defina "
                "MERCADOLIVRE_CLIENT_ID e MERCADOLIVRE_CLIENT_SECRET"
            )
        resp.raise_for_status()
        return self.parse(resp.json())

    def parse(self, data: dict) -> list[Deal]:
        deals = []
        for item in data.get("results", []):
            price = to_float(item.get("price"))
            if price is None or not item.get("permalink"):
                continue
            seller = item.get("seller") or {}
            deals.append(
                Deal(
                    source=self.name,
                    item_id=str(item["id"]),
                    title=item.get("title", ""),
                    url=item["permalink"],
                    price=price,
                    original_price=to_float(item.get("original_price")),
                    currency=item.get("currency_id", "BRL"),
                    image_url=(item.get("thumbnail") or "").replace("-I.jpg", "-O.jpg") or None,
                    store=seller.get("nickname"),
                )
            )
        return deals
