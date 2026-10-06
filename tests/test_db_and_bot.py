from unittest.mock import AsyncMock

from promobot.bot import PromoBot
from promobot.config import Settings
from promobot.db import Database
from promobot.formatting import brl, format_deal
from promobot.models import Deal
from promobot.sources.base import Source


def test_watches_crud():
    db = Database(":memory:")
    assert db.add_watch(1, "  Air Fryer ", 400) is True
    assert db.add_watch(1, "air fryer", 350) is False  # atualiza preço
    db.add_watch(2, "kindle", None)
    watches = db.list_watches(1)
    assert len(watches) == 1 and watches[0].max_price == 350
    assert len(db.list_watches()) == 2
    assert db.remove_watch(1, "AIR FRYER") is True
    assert db.remove_watch(2, str(db.list_watches(2)[0].id)) is True
    assert db.list_watches() == []


def test_sent_deals_resend_on_price_drop():
    db = Database(":memory:")
    assert db.should_send(1, "ml:1", 100)
    db.mark_sent(1, "ml:1", 100)
    assert not db.should_send(1, "ml:1", 100)
    assert not db.should_send(1, "ml:1", 97)
    assert db.should_send(1, "ml:1", 94)
    assert db.should_send("@canal", "ml:1", 100)


def test_chat_settings():
    db = Database(":memory:")
    assert db.get_min_discount(1, 20) == 20
    db.set_min_discount(1, 35, 20)
    assert db.get_min_discount(1, 20) == 35
    db.set_paused(1, True, 20)
    assert db.is_paused(1)


def test_format():
    assert brl(1234.5) == "R$ 1.234,50"
    text = format_deal(Deal("amazon", "1", "Kindle <novo>", "https://a?b=1&c=2", 450, 600, store="Amazon"), "kindle")
    assert "Kindle &lt;novo&gt;" in text
    assert "-25%" in text
    assert "<s>R$ 600,00</s>" in text
    assert 'href="https://a?b=1&amp;c=2"' in text


class FakeSource(Source):
    name = "fake"
    label = "Fake"

    def __init__(self, deals):
        self.deals = deals
        self.calls = 0

    async def search(self, keyword):
        self.calls += 1
        return self.deals


async def test_check_deals_sends_and_dedups(tmp_path, monkeypatch):
    monkeypatch.setattr("promobot.bot.SEND_DELAY", 0)
    settings = Settings(telegram_token="x", db_path=str(tmp_path / "db.sqlite"), channel_id="@canal")
    bot = PromoBot(settings)
    source = FakeSource(
        [
            Deal("fake", "1", "Air Fryer Mondial", "https://x/1", 300, 500),
            Deal("fake", "2", "Air Fryer Philco", "https://x/2", 490, 500),  # 2%: abaixo do mínimo
        ]
    )
    bot.sources = [source]
    bot.db.add_watch(10, "air fryer", None)
    bot.db.add_watch(11, "air fryer", None)

    tg = AsyncMock()
    sent = await bot.check_deals(tg)
    # chat 10, canal, chat 11 (canal já recebeu)
    assert sent == 3
    assert source.calls == 1  # mesma palavra buscada uma vez só
    assert tg.send_message.await_count == 3

    sent = await bot.check_deals(tg)
    assert sent == 0
