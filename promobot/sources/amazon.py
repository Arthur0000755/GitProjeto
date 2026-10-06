"""Amazon — Product Advertising API 5.0 (SearchItems), com assinatura AWS SigV4.

Requer conta no programa de Associados (https://associados.amazon.com.br) com
acesso liberado à PA-API. Os links retornados já contêm a sua tag de associado.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx

from promobot.models import Deal
from promobot.sources.base import Source, to_float

SERVICE = "ProductAdvertisingAPI"
PATH = "/paapi5/searchitems"
TARGET = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"

RESOURCES = [
    "ItemInfo.Title",
    "Images.Primary.Large",
    "Offers.Listings.Price",
    "Offers.Listings.SavingBasis",
    "Offers.Listings.MerchantInfo",
]


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def sign_v4(
    *,
    access_key: str,
    secret_key: str,
    region: str,
    host: str,
    path: str,
    payload: str,
    headers: dict[str, str],
    now: datetime | None = None,
) -> dict[str, str]:
    """Retorna os headers assinados (SigV4) para um POST na PA-API."""
    now = now or datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    all_headers = {k.lower(): v for k, v in headers.items()}
    all_headers["host"] = host
    all_headers["x-amz-date"] = amz_date

    signed_names = sorted(all_headers)
    canonical_headers = "".join(f"{k}:{all_headers[k].strip()}\n" for k in signed_names)
    signed_headers = ";".join(signed_names)
    canonical_request = "\n".join(
        [
            "POST",
            path,
            "",
            canonical_headers,
            signed_headers,
            hashlib.sha256(payload.encode()).hexdigest(),
        ]
    )
    scope = f"{date_stamp}/{region}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    k_signing = _hmac(
        _hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), date_stamp), region), SERVICE),
        "aws4_request",
    )
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    result = dict(headers)
    result["Host"] = host
    result["X-Amz-Date"] = amz_date
    result["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return result


class AmazonSource(Source):
    name = "amazon"
    label = "Amazon"

    def __init__(
        self,
        client: httpx.AsyncClient,
        access_key: str,
        secret_key: str,
        partner_tag: str,
        host: str = "webservices.amazon.com.br",
        region: str = "us-east-1",
        marketplace: str = "www.amazon.com.br",
        max_results: int = 10,
    ):
        # A PA-API retorna no máximo 10 itens por requisição.
        super().__init__(client, min(max_results, 10))
        self.access_key = access_key
        self.secret_key = secret_key
        self.partner_tag = partner_tag
        self.host = host
        self.region = region
        self.marketplace = marketplace

    async def search(self, keyword: str) -> list[Deal]:
        payload = json.dumps(
            {
                "Keywords": keyword,
                "PartnerTag": self.partner_tag,
                "PartnerType": "Associates",
                "Marketplace": self.marketplace,
                "SearchIndex": "All",
                "ItemCount": self.max_results,
                "Resources": RESOURCES,
            }
        )
        headers = sign_v4(
            access_key=self.access_key,
            secret_key=self.secret_key,
            region=self.region,
            host=self.host,
            path=PATH,
            payload=payload,
            headers={
                "content-encoding": "amz-1.0",
                "content-type": "application/json; charset=utf-8",
                "x-amz-target": TARGET,
            },
        )
        resp = await self.client.post(f"https://{self.host}{PATH}", content=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Amazon PA-API {resp.status_code}: {resp.text[:300]}")
        return self.parse(resp.json())

    def parse(self, data: dict) -> list[Deal]:
        items = (data.get("SearchResult") or {}).get("Items") or []
        deals = []
        for item in items:
            listings = (item.get("Offers") or {}).get("Listings") or []
            if not listings:
                continue
            listing = listings[0]
            price = to_float((listing.get("Price") or {}).get("Amount"))
            if price is None:
                continue
            title = ((item.get("ItemInfo") or {}).get("Title") or {}).get("DisplayValue", "")
            image = (((item.get("Images") or {}).get("Primary") or {}).get("Large") or {}).get("URL")
            deals.append(
                Deal(
                    source=self.name,
                    item_id=item["ASIN"],
                    title=title,
                    url=item.get("DetailPageURL", f"https://{self.marketplace}/dp/{item['ASIN']}"),
                    price=price,
                    original_price=to_float((listing.get("SavingBasis") or {}).get("Amount")),
                    currency=(listing.get("Price") or {}).get("Currency", "BRL"),
                    image_url=image,
                    store=(listing.get("MerchantInfo") or {}).get("Name"),
                )
            )
        return deals
