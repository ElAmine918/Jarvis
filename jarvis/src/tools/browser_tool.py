import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict
from urllib.parse import urlparse, quote

import httpx

from .base import Tool
from ..config import TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_USER_IDS

logger = logging.getLogger(__name__)

CHROMIUM_URL = "http://chromium:3000"


class HTMLToTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'head', 'meta', 'link', 'noscript'):
            self.in_script_or_style = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'head', 'meta', 'link', 'noscript'):
            self.in_script_or_style = False
        elif tag in ('p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'article', 'section'):
            self.text.append('\n')

    def handle_data(self, data):
        if not self.in_script_or_style:
            text = data.strip()
            if text:
                self.text.append(text + ' ')

    def get_text(self):
        return "".join(self.text).strip()


class BrowserNavigateTool(Tool):

    @property
    def name(self) -> str:
        return "browse_internet"

    @property
    def description(self) -> str:
        return (
            "Navigue sur le web avec un vrai navigateur Chromium autonome. "
            "Exécute le JavaScript des sites modernes (React, SPAs, actualités), extrait le texte réellement affiché, "
            "peut effectuer des recherches Google/DuckDuckGo, et envoie automatiquement une capture d'écran (photo) sur Telegram."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "url_or_search": {
                    "type": "string",
                    "description": "L'URL complète à visiter (ex: https://...) OU des mots-clés de recherche (ex: 'nouvelles canada', 'meteo paris')."
                },
                "send_screenshot": {
                    "type": "boolean",
                    "description": "Si true, prend une capture d'écran visuelle et l'envoie sur Telegram à l'utilisateur.",
                    "default": True
                }
            },
            "required": ["url_or_search"]
        }

    async def execute(self, url_or_search: str, send_screenshot: bool = True, **kwargs) -> str:
        target = url_or_search.strip()
        
        # Si ce n'est pas une URL, on transforme en recherche Google
        if not target.startswith("http://") and not target.startswith("https://"):
            target = f"https://www.google.com/search?q={quote(target)}&hl=fr"

        logger.info(f"Navigateur Chromium : navigation vers {target}")

        rendered_text = ""
        screenshot_sent = False

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Récupération du contenu rendu avec exécution JavaScript
            try:
                content_payload = {
                    "url": target,
                    "waitForTimeout": 3000,
                    "gotoOptions": {
                        "waitUntil": "domcontentloaded",
                        "timeout": 20000
                    }
                }
                res = await client.post(f"{CHROMIUM_URL}/content", json=content_payload)
                if res.status_code == 200:
                    parser = HTMLToTextParser()
                    parser.feed(res.text)
                    raw_text = parser.get_text()
                    raw_text = re.sub(r'\n\s*\n', '\n\n', raw_text)
                    rendered_text = raw_text[:6000] + ("\n...[Page tronquée]" if len(raw_text) > 6000 else "")
                else:
                    rendered_text = f"Erreur de rendu Chromium (Code {res.status_code})"
            except Exception as e:
                logger.error(f"Erreur rendu Chromium: {e}")
                rendered_text = f"Impossible de charger la page : {e}"

            # 2. Capture d'écran et envoi sur Telegram si demandé
            if send_screenshot and TELEGRAM_BOT_TOKEN and ALLOWED_TELEGRAM_USER_IDS:
                try:
                    screen_payload = {
                        "url": target,
                        "waitForTimeout": 2500,
                        "options": {
                            "type": "jpeg",
                            "quality": 85,
                            "fullPage": False
                        }
                    }
                    screen_res = await client.post(f"{CHROMIUM_URL}/screenshot", json=screen_payload)
                    if screen_res.status_code == 200 and len(screen_res.content) > 1000:
                        admin_id = ALLOWED_TELEGRAM_USER_IDS[0]
                        files = {
                            "photo": ("screenshot.jpg", screen_res.content, "image/jpeg")
                        }
                        data = {
                            "chat_id": admin_id,
                            "caption": f"📸 Page web consultée :\n{target}"
                        }
                        await client.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                            data=data,
                            files=files
                        )
                        screenshot_sent = True
                except Exception as e:
                    logger.warning(f"Échec envoi screenshot Telegram: {e}")

        status_msg = "📸 [Capture d'écran envoyée sur Telegram]\n\n" if screenshot_sent else ""
        return f"{status_msg}Contenu visible sur la page ({target}) :\n\n{rendered_text}"
