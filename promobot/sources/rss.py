"""Feeds RSS/Atom genéricos — cobre sites agregadores (Pelando, Promobit, blogs de
ofertas) e lojas que publicam feeds (Magalu, KaBuM!, Casas Bahia via agregadores, etc.).

Os itens são filtrados pela palavra-chave no título e os preços extraídos do texto
("De R$ 199,90 por R$ 129,90").
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urlparse

import httpx

from promobot.models import Deal
from promobot.sources.base import USER_AGENT, Source, parse_brl

log = logging.getLogger(__name__)

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
_TAG_RE = re.compile(r"<[^>]+>")
_IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)")

# Evita baixar todos os feeds a cada palavra-chave do mesmo ciclo.
CACHE_SECONDS = 120


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def parse_feed(xml_text: str, feed_url: str) -> list[dict]:
    """Converte um feed RSS 2.0 ou Atom em uma lista de dicts {title, link, summary, image}."""
    root = ET.fromstring(xml_text)
    entries = []
    for item in root.iter("item"):
        image = None
        for tag in (f"{MEDIA}content", f"{MEDIA}thumbnail", "enclosure"):
            el = item.find(tag)
            if el is not None and el.get("url"):
                image = el.get("url")
                break
        entries.append(
            {
                "title": _text(item.find("title")),
                "link": _text(item.find("link")),
                "summary": _text(item.find("description")),
                "image": image,
            }
        )
    for entry in root.iter(f"{ATOM}entry"):
        link_el = entry.find(f"{ATOM}link")
        entries.append(
            {
                "title": _text(entry.find(f"{ATOM}title")),
                "link": link_el.get("href", "") if link_el is not None else "",
                "summary": _text(entry.find(f"{ATOM}summary"))
                or _text(entry.find(f"{ATOM}content")),
                "image": None,
            }
        )
    for e in entries:
        if not e["image"]:
            match = _IMG_RE.search(e["summary"])
            e["image"] = match.group(1) if match else None
        e["summary"] = unescape(_TAG_RE.sub(" ", e["summary"]))
        e["title"] = unescape(e["title"])
        e["feed"] = urlparse(feed_url).netloc
    return entries


def matches(keyword: str, title: str) -> bool:
    """Todas as palavras da busca precisam aparecer no título."""
    title = title.lower()
    return all(word in title for word in keyword.lower().split())


class RssSource(Source):
    name = "rss"
    label = "Feeds RSS"

    def __init__(self, client: httpx.AsyncClient, feeds: list[str], max_results: int = 20):
        super().__init__(client, max_results)
        self.feeds = feeds
        self._cache: list[dict] = []
        self._cache_time = 0.0
        self._lock = asyncio.Lock()

    async def _fetch(self, url: str) -> list[dict]:
        try:
            resp = await self.client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return parse_feed(resp.text, url)
        except Exception as exc:  # um feed com problema não derruba os outros
            log.warning("Falha ao ler feed %s: %s", url, exc)
            return []

    async def _entries(self) -> list[dict]:
        async with self._lock:
            if time.time() - self._cache_time > CACHE_SECONDS:
                results = await asyncio.gather(*(self._fetch(u) for u in self.feeds))
                self._cache = [e for feed in results for e in feed]
                self._cache_time = time.time()
            return self._cache

    async def search(self, keyword: str) -> list[Deal]:
        deals = []
        for e in await self._entries():
            if not e["link"] or not matches(keyword, e["title"]):
                continue
            prices = parse_brl(f"{e['title']} {e['summary']}")
            if not prices:
                continue
            price = min(prices)
            original = max(prices) if len(prices) > 1 and max(prices) > price else None
            deals.append(
                Deal(
                    source=self.name,
                    item_id=hashlib.sha1(e["link"].encode()).hexdigest()[:16],
                    title=e["title"],
                    url=e["link"],
                    price=price,
                    original_price=original,
                    image_url=e["image"],
                    store=e["feed"],
                )
            )
            if len(deals) >= self.max_results:
                break
        return deals
