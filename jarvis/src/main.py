"""
Point d'entrée de Jarvis.
Lance en parallèle :
  - Le bot Telegram (polling)
  - Le serveur FastAPI (pour Open WebUI)
"""

import asyncio
import logging
import sys

import uvicorn

from .agent import JarvisAgent
from .api import app as fastapi_app
from .bot import build_app as build_telegram_app
from .config import API_HOST, API_PORT, LOG_LEVEL, TELEGRAM_BOT_TOKEN

# Configuration du logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def run_telegram(agent: JarvisAgent):
    """Lance le bot Telegram en polling."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN non défini — bot Telegram désactivé.")
        return

    app = build_telegram_app(agent)
    await app.initialize()
    await app.start()
    logger.info("✅ Bot Telegram démarré")
    await app.updater.start_polling(drop_pending_updates=False)

    # Maintenir le bot en vie jusqu'à l'arrêt
    stop_event = asyncio.Event()
    await stop_event.wait()


async def run_api(agent: JarvisAgent):
    """Lance le serveur FastAPI (pour Open WebUI)."""
    fastapi_app.state.agent = agent
    config = uvicorn.Config(
        app=fastapi_app,
        host=API_HOST,
        port=API_PORT,
        log_level=LOG_LEVEL.lower(),
        access_log=False,
    )
    server = uvicorn.Server(config)
    logger.info(f"✅ API Jarvis démarrée sur http://{API_HOST}:{API_PORT}")
    await server.serve()


from .logger_db import init_db


async def main():
    logger.info("🚀 Démarrage de Jarvis...")
    init_db()

    # Créer et initialiser l'agent (partagé entre Telegram et l'API)
    agent = JarvisAgent()
    await agent.init()
    logger.info("✅ Agent initialisé (mémoire SQLite prête)")

    # Recharger les rappels planifiés survivant au redémarrage
    from .tools.scheduler_tool import SchedulerTool

    await SchedulerTool.reload_pending_jobs()
    logger.info("✅ Rappels planifiés rechargés")

    # Lancer Telegram et l'API en parallèle
    await asyncio.gather(
        run_telegram(agent),
        run_api(agent),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt de Jarvis.")
