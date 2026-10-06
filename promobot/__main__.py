"""Ponto de entrada: python -m promobot"""

import logging

from promobot.bot import PromoBot
from promobot.config import Settings


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # httpx loga cada requisição em INFO (inclusive a URL com o token do bot)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if not settings.admin_ids:
        logging.warning("ADMIN_IDS vazio: qualquer pessoa poderá usar o bot!")

    app = PromoBot(settings).build_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
