"""Configuração lida de variáveis de ambiente (ou do arquivo .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


def _int_list(value: str | None) -> list[int]:
    if not value:
        return []
    return [int(v) for v in value.replace(" ", "").split(",") if v]


def _str_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "sim", "yes", "on"}


@dataclass
class Settings:
    telegram_token: str
    admin_ids: list[int] = field(default_factory=list)
    channel_id: str | None = None

    check_interval_minutes: int = 30
    default_min_discount: int = 20
    max_results_per_source: int = 20
    db_path: str = "data/promobot.db"
    log_level: str = "INFO"

    # Mercado Livre
    mercadolivre_enabled: bool = True
    mercadolivre_site: str = "MLB"
    mercadolivre_client_id: str | None = None
    mercadolivre_client_secret: str | None = None
    mercadolivre_access_token: str | None = None

    # Shopee (API de afiliados)
    shopee_app_id: str | None = None
    shopee_secret: str | None = None

    # Amazon (Product Advertising API 5.0)
    amazon_access_key: str | None = None
    amazon_secret_key: str | None = None
    amazon_partner_tag: str | None = None
    amazon_host: str = "webservices.amazon.com.br"
    amazon_region: str = "us-east-1"
    amazon_marketplace: str = "www.amazon.com.br"

    # AliExpress (API de afiliados)
    aliexpress_app_key: str | None = None
    aliexpress_app_secret: str | None = None
    aliexpress_tracking_id: str | None = None

    # Feeds RSS genéricos (Pelando, Promobit, blogs de ofertas, Magalu, etc.)
    rss_feeds: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Defina TELEGRAM_BOT_TOKEN no arquivo .env")

        env = os.getenv
        return cls(
            telegram_token=token,
            admin_ids=_int_list(env("ADMIN_IDS")),
            channel_id=env("TELEGRAM_CHANNEL_ID") or None,
            check_interval_minutes=int(env("CHECK_INTERVAL_MINUTES", "30")),
            default_min_discount=int(env("MIN_DISCOUNT", "20")),
            max_results_per_source=int(env("MAX_RESULTS_PER_SOURCE", "20")),
            db_path=env("DB_PATH", "data/promobot.db"),
            log_level=env("LOG_LEVEL", "INFO").upper(),
            mercadolivre_enabled=_bool(env("MERCADOLIVRE_ENABLED"), True),
            mercadolivre_site=env("MERCADOLIVRE_SITE", "MLB"),
            mercadolivre_client_id=env("MERCADOLIVRE_CLIENT_ID") or None,
            mercadolivre_client_secret=env("MERCADOLIVRE_CLIENT_SECRET") or None,
            mercadolivre_access_token=env("MERCADOLIVRE_ACCESS_TOKEN") or None,
            shopee_app_id=env("SHOPEE_APP_ID") or None,
            shopee_secret=env("SHOPEE_SECRET") or None,
            amazon_access_key=env("AMAZON_ACCESS_KEY") or None,
            amazon_secret_key=env("AMAZON_SECRET_KEY") or None,
            amazon_partner_tag=env("AMAZON_PARTNER_TAG") or None,
            amazon_host=env("AMAZON_HOST", "webservices.amazon.com.br"),
            amazon_region=env("AMAZON_REGION", "us-east-1"),
            amazon_marketplace=env("AMAZON_MARKETPLACE", "www.amazon.com.br"),
            aliexpress_app_key=env("ALIEXPRESS_APP_KEY") or None,
            aliexpress_app_secret=env("ALIEXPRESS_APP_SECRET") or None,
            aliexpress_tracking_id=env("ALIEXPRESS_TRACKING_ID") or None,
            rss_feeds=_str_list(env("RSS_FEEDS")),
        )
