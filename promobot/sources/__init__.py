"""Registro das fontes de ofertas habilitadas conforme a configuração."""

from __future__ import annotations

import logging

import httpx

from promobot.config import Settings
from promobot.sources.aliexpress import AliExpressSource
from promobot.sources.amazon import AmazonSource
from promobot.sources.base import Source
from promobot.sources.mercadolivre import MercadoLivreSource
from promobot.sources.rss import RssSource
from promobot.sources.shopee import ShopeeSource

log = logging.getLogger(__name__)

__all__ = ["Source", "build_sources"]


def build_sources(settings: Settings, client: httpx.AsyncClient) -> list[Source]:
    """Cria as fontes que têm credenciais configuradas."""
    n = settings.max_results_per_source
    sources: list[Source] = []

    if settings.mercadolivre_enabled:
        sources.append(
            MercadoLivreSource(
                client,
                n,
                site=settings.mercadolivre_site,
                client_id=settings.mercadolivre_client_id,
                client_secret=settings.mercadolivre_client_secret,
                access_token=settings.mercadolivre_access_token,
            )
        )

    if settings.shopee_app_id and settings.shopee_secret:
        sources.append(ShopeeSource(client, settings.shopee_app_id, settings.shopee_secret, n))
    else:
        log.info("Shopee desabilitada (defina SHOPEE_APP_ID e SHOPEE_SECRET)")

    if settings.amazon_access_key and settings.amazon_secret_key and settings.amazon_partner_tag:
        sources.append(
            AmazonSource(
                client,
                settings.amazon_access_key,
                settings.amazon_secret_key,
                settings.amazon_partner_tag,
                host=settings.amazon_host,
                region=settings.amazon_region,
                marketplace=settings.amazon_marketplace,
                max_results=n,
            )
        )
    else:
        log.info("Amazon desabilitada (defina AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY e AMAZON_PARTNER_TAG)")

    if settings.aliexpress_app_key and settings.aliexpress_app_secret:
        sources.append(
            AliExpressSource(
                client,
                settings.aliexpress_app_key,
                settings.aliexpress_app_secret,
                settings.aliexpress_tracking_id,
                n,
            )
        )
    else:
        log.info("AliExpress desabilitado (defina ALIEXPRESS_APP_KEY e ALIEXPRESS_APP_SECRET)")

    if settings.rss_feeds:
        sources.append(RssSource(client, settings.rss_feeds, n))

    log.info("Fontes ativas: %s", ", ".join(s.label for s in sources) or "nenhuma")
    return sources
