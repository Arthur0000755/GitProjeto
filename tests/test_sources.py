import json
from datetime import datetime, timezone

import httpx
import pytest

from promobot.models import Deal
from promobot.monitor import filter_deals, search_all
from promobot.sources.aliexpress import AliExpressSource, sign_params
from promobot.sources.amazon import AmazonSource, sign_v4
from promobot.sources.base import parse_brl
from promobot.sources.mercadolivre import MercadoLivreSource
from promobot.sources.rss import RssSource
from promobot.sources.shopee import ShopeeSource


def client_with(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_parse_brl():
    assert parse_brl("De R$ 1.299,90 por R$999") == [1299.9, 999.0]
    assert parse_brl("sem preço") == []


def test_discount():
    assert Deal("x", "1", "t", "u", 80, 100).discount_pct == 20.0
    assert Deal("x", "1", "t", "u", 80, None).discount_pct == 0.0
    assert Deal("x", "1", "t", "u", 120, 100).discount_pct == 0.0


async def test_mercadolivre_search():
    def handler(request: httpx.Request):
        assert request.url.path == "/sites/MLB/search"
        assert request.url.params["q"] == "air fryer"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "MLB1",
                        "title": "Air Fryer Mondial 4L",
                        "price": 299.9,
                        "original_price": 499.9,
                        "permalink": "https://produto.mercadolivre.com.br/MLB1",
                        "thumbnail": "http://img/abc-I.jpg",
                        "currency_id": "BRL",
                        "seller": {"nickname": "LOJA"},
                    },
                    {"id": "MLB2", "title": "sem preço", "permalink": "x"},
                ]
            },
        )

    async with client_with(handler) as client:
        deals = await MercadoLivreSource(client).search("air fryer")
    assert len(deals) == 1
    assert deals[0].discount_pct == 40.0
    assert deals[0].image_url == "http://img/abc-O.jpg"
    assert deals[0].store == "LOJA"


async def test_mercadolivre_client_credentials():
    calls = []

    def handler(request: httpx.Request):
        calls.append(request.url.path)
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        assert request.headers["Authorization"] == "Bearer TOKEN"
        return httpx.Response(200, json={"results": []})

    async with client_with(handler) as client:
        src = MercadoLivreSource(client, client_id="id", client_secret="secret")
        await src.search("a")
        await src.search("b")
    assert calls == ["/oauth/token", "/sites/MLB/search", "/sites/MLB/search"]


async def test_shopee_search_signs_request():
    def handler(request: httpx.Request):
        auth = request.headers["Authorization"]
        assert auth.startswith("SHA256 Credential=app, Timestamp=")
        body = json.loads(request.content)
        assert body["variables"]["keyword"] == "fone"
        return httpx.Response(
            200,
            json={
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": 10,
                                "productName": "Fone Bluetooth",
                                "priceMin": "50.00",
                                "priceDiscountRate": 50,
                                "offerLink": "https://s.shopee.com.br/abc",
                                "imageUrl": "https://img",
                                "shopName": "Loja",
                            }
                        ]
                    }
                }
            },
        )

    async with client_with(handler) as client:
        deals = await ShopeeSource(client, "app", "secret").search("fone")
    assert deals[0].price == 50.0
    assert deals[0].original_price == 100.0
    assert deals[0].url == "https://s.shopee.com.br/abc"


def test_sigv4_known_vector():
    headers = sign_v4(
        access_key="AKID",
        secret_key="SECRET",
        region="us-east-1",
        host="webservices.amazon.com.br",
        path="/paapi5/searchitems",
        payload="{}",
        headers={"content-type": "application/json"},
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    assert headers["X-Amz-Date"] == "20240101T000000Z"
    assert headers["Authorization"].startswith(
        "AWS4-HMAC-SHA256 Credential=AKID/20240101/us-east-1/ProductAdvertisingAPI/aws4_request, "
        "SignedHeaders=content-type;host;x-amz-date, Signature="
    )
    # assinatura é determinística
    again = sign_v4(
        access_key="AKID",
        secret_key="SECRET",
        region="us-east-1",
        host="webservices.amazon.com.br",
        path="/paapi5/searchitems",
        payload="{}",
        headers={"content-type": "application/json"},
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    assert again["Authorization"] == headers["Authorization"]


async def test_amazon_search():
    def handler(request: httpx.Request):
        assert request.url.host == "webservices.amazon.com.br"
        assert "AWS4-HMAC-SHA256" in request.headers["Authorization"]
        body = json.loads(request.content)
        assert body["PartnerTag"] == "tag-20"
        return httpx.Response(
            200,
            json={
                "SearchResult": {
                    "Items": [
                        {
                            "ASIN": "B0TEST",
                            "DetailPageURL": "https://www.amazon.com.br/dp/B0TEST?tag=tag-20",
                            "ItemInfo": {"Title": {"DisplayValue": "Kindle 11ª geração"}},
                            "Offers": {
                                "Listings": [
                                    {
                                        "Price": {"Amount": 449.0, "Currency": "BRL"},
                                        "SavingBasis": {"Amount": 599.0},
                                    }
                                ]
                            },
                        },
                        {"ASIN": "B0NOOFFER"},
                    ]
                }
            },
        )

    async with client_with(handler) as client:
        deals = await AmazonSource(client, "ak", "sk", "tag-20").search("kindle")
    assert len(deals) == 1
    assert deals[0].item_id == "B0TEST"
    assert deals[0].discount_pct == 25.0


def test_aliexpress_sign():
    sig = sign_params({"b": "2", "a": "1"}, "s")
    assert sig == sign_params({"a": "1", "b": "2"}, "s")
    assert sig.isupper() and len(sig) == 64


async def test_aliexpress_search():
    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "aliexpress_affiliate_product_query_response": {
                    "resp_result": {
                        "result": {
                            "products": {
                                "product": [
                                    {
                                        "product_id": 1,
                                        "product_title": "Smartwatch",
                                        "target_sale_price": "90.00",
                                        "target_original_price": "180.00",
                                        "promotion_link": "https://s.click.aliexpress.com/x",
                                    }
                                ]
                            }
                        }
                    }
                }
            },
        )

    async with client_with(handler) as client:
        deals = await AliExpressSource(client, "k", "s").search("smartwatch")
    assert deals[0].discount_pct == 50.0


RSS = """<?xml version="1.0"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>Notebook Acer Aspire 5 - R$ 2.999,00</title>
<link>https://site.com/1</link>
<description>&lt;p&gt;De R$ 3.999,00 por R$ 2.999,00&lt;/p&gt;</description>
<media:content url="https://img/1.jpg"/></item>
<item><title>Geladeira Brastemp</title><link>https://site.com/2</link>
<description>Por R$ 3.000</description></item>
</channel></rss>"""


async def test_rss_source():
    async with client_with(lambda r: httpx.Response(200, text=RSS)) as client:
        deals = await RssSource(client, ["https://site.com/feed"]).search("notebook acer")
    assert len(deals) == 1
    assert deals[0].price == 2999.0
    assert deals[0].original_price == 3999.0
    assert deals[0].image_url == "https://img/1.jpg"
    assert deals[0].store == "site.com"


async def test_search_all_isolates_failures():
    class Boom(MercadoLivreSource):
        label = "Boom"

        async def search(self, keyword):
            raise RuntimeError("fora do ar")

    async with client_with(lambda r: httpx.Response(200, text=RSS)) as client:
        result = await search_all([Boom(client), RssSource(client, ["https://x/feed"])], "notebook")
    assert result.errors == {"Boom": "fora do ar"}
    assert len(result.deals) == 1


def test_filter_deals():
    deals = [
        Deal("a", "1", "Air Fryer 4L", "u", 300, 500),  # 40%
        Deal("a", "1", "Air Fryer 4L", "u", 300, 500),  # duplicada
        Deal("b", "2", "Air Fryer 3L", "u", 450, 500),  # 10%
        Deal("c", "3", "Air Fryer 5L", "u", 600, 1200),  # 50%, acima do preço máx
        Deal("d", "4", "Liquidificador", "u", 50, 100),  # não bate a busca
    ]
    result = filter_deals(deals, "air fryer", min_discount=20, max_price=500)
    assert [d.item_id for d in result] == ["1"]
    result = filter_deals(deals, "AIR fryer")
    assert [d.item_id for d in result] == ["3", "1", "2"]
