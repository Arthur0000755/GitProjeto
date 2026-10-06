"""Comandos do Telegram e a tarefa periódica que procura promoções."""

from __future__ import annotations

import asyncio
import logging
from functools import wraps
from html import escape

import httpx
from telegram import LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from promobot.config import Settings
from promobot.db import Database
from promobot.formatting import brl, format_deal, format_deal_short
from promobot.models import Deal
from promobot.monitor import filter_deals, search_all
from promobot.sources import Source, build_sources
from promobot.sources.base import USER_AGENT

log = logging.getLogger(__name__)

# Máximo de ofertas enviadas por palavra-chave a cada ciclo (evita flood).
MAX_ALERTS_PER_WATCH = 5
# Intervalo entre mensagens para respeitar os limites do Telegram.
SEND_DELAY = 1.5

HELP = """\
🤖 <b>Bot de Promoções</b>

Monitoro ofertas em: {sources}

<b>Comandos</b>
/add <i>termo</i> [preço máx] — monitora um produto
   ex.: <code>/add iphone 15 4500</code>
/remove <i>termo ou id</i> — para de monitorar
/lista — mostra os produtos monitorados
/buscar <i>termo</i> — busca agora em todas as lojas
/desconto <i>N</i> — desconto mínimo para alertas (atual: {discount}%)
/pausar e /retomar — pausa/retoma os alertas
/verificar — força uma verificação agora
/status — fontes ativas e configurações
"""


class PromoBot:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.db_path)
        self.http: httpx.AsyncClient | None = None
        self.sources: list[Source] = []
        self._check_lock = asyncio.Lock()

    # --- ciclo de vida ------------------------------------------------------

    def build_application(self) -> Application:
        app = (
            Application.builder()
            .token(self.settings.telegram_token)
            .post_init(self._post_init)
            .post_shutdown(self._post_shutdown)
            .build()
        )
        handlers = {
            "start": self.cmd_help,
            "help": self.cmd_help,
            "ajuda": self.cmd_help,
            "add": self.cmd_add,
            "remove": self.cmd_remove,
            "lista": self.cmd_list,
            "list": self.cmd_list,
            "buscar": self.cmd_search,
            "desconto": self.cmd_discount,
            "pausar": self.cmd_pause,
            "retomar": self.cmd_resume,
            "verificar": self.cmd_check,
            "status": self.cmd_status,
        }
        for name, callback in handlers.items():
            app.add_handler(CommandHandler(name, self._restricted(callback)))
        app.add_error_handler(self._on_error)

        app.job_queue.run_repeating(
            self.job_check,
            interval=self.settings.check_interval_minutes * 60,
            first=30,
            name="check-deals",
        )
        app.job_queue.run_repeating(self.job_prune, interval=86400, first=3600, name="prune")
        return app

    async def _post_init(self, app: Application) -> None:
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"},
            follow_redirects=True,
        )
        self.sources = build_sources(self.settings, self.http)
        await app.bot.set_my_commands(
            [
                ("add", "Monitorar um produto"),
                ("remove", "Parar de monitorar"),
                ("lista", "Produtos monitorados"),
                ("buscar", "Buscar agora em todas as lojas"),
                ("desconto", "Definir desconto mínimo"),
                ("verificar", "Verificar promoções agora"),
                ("status", "Fontes e configurações"),
                ("help", "Ajuda"),
            ]
        )

    async def _post_shutdown(self, app: Application) -> None:
        if self.http:
            await self.http.aclose()
        self.db.close()

    async def _on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("Erro ao processar update", exc_info=context.error)

    def _restricted(self, func):
        """Só permite os usuários listados em ADMIN_IDS (se definido)."""

        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if self.settings.admin_ids and (not user or user.id not in self.settings.admin_ids):
                if update.effective_message:
                    await update.effective_message.reply_text(
                        f"⛔ Acesso negado. Seu ID é {user.id if user else '?'}."
                    )
                return
            return await func(update, context)

        return wrapper

    # --- comandos -----------------------------------------------------------

    def _min_discount(self, chat_id: int) -> int:
        return self.db.get_min_discount(chat_id, self.settings.default_min_discount)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        text = HELP.format(
            sources=", ".join(s.label for s in self.sources) or "nenhuma fonte configurada",
            discount=self._min_discount(chat_id),
        )
        await update.effective_message.reply_html(text)

    async def cmd_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = list(context.args)
        if not args:
            await update.effective_message.reply_html(
                "Uso: <code>/add termo [preço máximo]</code>\nex.: <code>/add air fryer 400</code>"
            )
            return
        max_price = None
        last = args[-1].replace("R$", "").replace(".", "").replace(",", ".")
        if len(args) > 1:
            try:
                max_price = float(last)
                args = args[:-1]
            except ValueError:
                pass
        keyword = " ".join(args).strip().lower()
        if len(keyword) < 2:
            await update.effective_message.reply_text("Termo muito curto.")
            return
        is_new = self.db.add_watch(update.effective_chat.id, keyword, max_price)
        limit = f" até {brl(max_price)}" if max_price else ""
        verb = "Monitorando" if is_new else "Atualizado"
        await update.effective_message.reply_html(
            f"✅ {verb}: <b>{escape(keyword)}</b>{limit}\n"
            f"Desconto mínimo: {self._min_discount(update.effective_chat.id)}%"
        )

    async def cmd_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.effective_message.reply_html("Uso: <code>/remove termo</code> ou <code>/remove id</code>")
            return
        target = " ".join(context.args)
        if self.db.remove_watch(update.effective_chat.id, target):
            await update.effective_message.reply_text(f"🗑️ Removido: {target}")
        else:
            await update.effective_message.reply_text("Não encontrei esse item. Veja /lista.")

    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        watches = self.db.list_watches(chat_id)
        if not watches:
            await update.effective_message.reply_html(
                "Nenhum produto monitorado. Use <code>/add termo</code>."
            )
            return
        lines = [f"📋 <b>Monitorando</b> (desconto mín. {self._min_discount(chat_id)}%)"]
        if self.db.is_paused(chat_id):
            lines.append("⏸️ <i>Alertas pausados — use /retomar</i>")
        for w in watches:
            limit = f" — até {brl(w.max_price)}" if w.max_price else ""
            lines.append(f"<code>{w.id}</code> · {escape(w.keyword)}{limit}")
        await update.effective_message.reply_html("\n".join(lines))

    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        keyword = " ".join(context.args).strip()
        if not keyword:
            await update.effective_message.reply_html("Uso: <code>/buscar termo</code>")
            return
        msg = await update.effective_message.reply_text(f"🔎 Buscando “{keyword}”...")
        result = await search_all(self.sources, keyword)
        deals = filter_deals(result.deals, keyword)[:15]
        if not deals:
            text = f"Nada encontrado para <b>{escape(keyword)}</b>."
        else:
            text = f"🔎 <b>{escape(keyword)}</b> — melhores descontos:\n\n" + "\n".join(
                format_deal_short(d) for d in deals
            )
        if result.errors:
            text += "\n\n⚠️ Falharam: " + escape(", ".join(result.errors))
        await msg.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

    async def cmd_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        try:
            value = int(context.args[0].rstrip("%"))
            if not 0 <= value <= 95:
                raise ValueError
        except (IndexError, ValueError):
            await update.effective_message.reply_html(
                f"Uso: <code>/desconto 30</code> (0 a 95). Atual: {self._min_discount(chat_id)}%"
            )
            return
        self.db.set_min_discount(chat_id, value, self.settings.default_min_discount)
        await update.effective_message.reply_text(f"✅ Desconto mínimo: {value}%")

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.db.set_paused(update.effective_chat.id, True, self.settings.default_min_discount)
        await update.effective_message.reply_text("⏸️ Alertas pausados. Use /retomar para voltar.")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.db.set_paused(update.effective_chat.id, False, self.settings.default_min_discount)
        await update.effective_message.reply_text("▶️ Alertas retomados.")

    async def cmd_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self._check_lock.locked():
            await update.effective_message.reply_text("Já existe uma verificação em andamento.")
            return
        await update.effective_message.reply_text("🔄 Verificando promoções...")
        sent = await self.check_deals(context.bot)
        await update.effective_message.reply_text(f"✅ Verificação concluída: {sent} alerta(s) enviado(s).")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        s = self.settings
        lines = [
            "⚙️ <b>Status</b>",
            f"Fontes ativas: {escape(', '.join(x.label for x in self.sources) or 'nenhuma')}",
            f"Intervalo: {s.check_interval_minutes} min",
            f"Desconto mínimo deste chat: {self._min_discount(update.effective_chat.id)}%",
            f"Produtos monitorados (total): {len(self.db.list_watches())}",
            f"Canal: {escape(s.channel_id) if s.channel_id else 'não configurado'}",
            f"Seu ID: <code>{update.effective_user.id}</code>",
        ]
        await update.effective_message.reply_html("\n".join(lines))

    # --- verificação periódica ---------------------------------------------

    async def job_check(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self._check_lock.locked():
            return
        await self.check_deals(context.bot)

    async def job_prune(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        removed = self.db.prune_sent(30)
        log.info("Limpeza: %d registros antigos removidos", removed)

    async def check_deals(self, bot) -> int:
        """Procura ofertas para todas as palavras monitoradas e envia os alertas."""
        async with self._check_lock:
            watches = self.db.list_watches()
            if not watches or not self.sources:
                return 0

            # Uma busca por palavra-chave, mesmo que vários chats monitorem a mesma.
            cache: dict[str, list[Deal]] = {}
            sent = 0
            for watch in watches:
                if self.db.is_paused(watch.chat_id):
                    continue
                if watch.keyword not in cache:
                    cache[watch.keyword] = (await search_all(self.sources, watch.keyword)).deals
                min_discount = self._min_discount(watch.chat_id)
                deals = filter_deals(cache[watch.keyword], watch.keyword, min_discount, watch.max_price)

                destinations = [watch.chat_id]
                if self.settings.channel_id:
                    destinations.append(self.settings.channel_id)

                count = 0
                for deal in deals:
                    if count >= MAX_ALERTS_PER_WATCH:
                        break
                    delivered = False
                    for dest in destinations:
                        dest_key = str(dest)
                        if not self.db.should_send(dest_key, deal.key, deal.price):
                            continue
                        if await self.send_deal(bot, dest, deal, watch.keyword):
                            self.db.mark_sent(dest_key, deal.key, deal.price)
                            delivered = True
                            sent += 1
                    if delivered:
                        count += 1
            log.info("Verificação concluída: %d alerta(s) enviado(s)", sent)
            return sent

    async def send_deal(self, bot, chat_id: int | str, deal: Deal, keyword: str) -> bool:
        text = format_deal(deal, keyword)
        for attempt in range(3):
            try:
                if deal.image_url and len(text) <= 1024:
                    try:
                        await bot.send_photo(
                            chat_id, deal.image_url, caption=text, parse_mode=ParseMode.HTML
                        )
                    except RetryAfter:
                        raise
                    except TelegramError:
                        # imagem inválida/inacessível: envia só o texto
                        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
                else:
                    await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
                await asyncio.sleep(SEND_DELAY)
                return True
            except RetryAfter as exc:
                wait = exc.retry_after
                wait = wait.total_seconds() if hasattr(wait, "total_seconds") else float(wait)
                await asyncio.sleep(wait + 1)
            except TelegramError as exc:
                log.warning("Falha ao enviar oferta para %s: %s", chat_id, exc)
                return False
        return False
