import logging
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote

import httpx

from jarvis.tools.base import Tool
from jarvis.web_reader import _is_safe_url

logger = logging.getLogger(__name__)

CHROMIUM_URL = "http://chromium:3000"


class HTMLToTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "meta", "link", "noscript"):
            self.in_script_or_style = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "meta", "link", "noscript"):
            self.in_script_or_style = False
        elif tag in (
            "p",
            "br",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "article",
            "section",
        ):
            self.text.append("\n")

    def handle_data(self, data):
        if not self.in_script_or_style:
            text = data.strip()
            if text:
                self.text.append(text + " ")

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
            "Exécute le JavaScript des sites modernes, extrait le texte réellement affiché. "
            "IMPORTANT: Pour toute recherche web générale, tu DOIS construire une URL Google Search exacte (ex: https://www.google.com/search?q=ta+recherche) et ne JAMAIS utiliser Bing ou d'autres moteurs."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "url_or_search": {
                    "type": "string",
                    "description": "L'URL complète à visiter (ex: https://...) OU des mots-clés de recherche (ex: 'nouvelles canada', 'meteo paris').",
                }
            },
            "required": ["url_or_search"],
        }

    async def execute(self, url_or_search: str, **kwargs) -> str:
        target = url_or_search.strip()

        # Si ce n'est pas une URL, on transforme en recherche Google
        if not target.startswith("http://") and not target.startswith("https://"):
            target = f"https://www.google.com/search?q={quote(target)}&hl=fr"

        # C-04 : Validation SSRF — même protection que web_reader.py
        if not _is_safe_url(target):
            logger.warning(f"Tentative SSRF bloquée dans browse_internet vers {target}")
            return "🚫 URL bloquée. Les adresses IP locales, privées, Tailscale et les schémas non-HTTPS sont interdits."

        logger.info(f"Navigateur Chromium : navigation vers {target}")

        rendered_text = ""

        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                content_payload = {
                    "url": target,
                    "waitForTimeout": 2500,
                    "gotoOptions": {"waitUntil": "domcontentloaded", "timeout": 15000},
                }
                res = await client.post(f"{CHROMIUM_URL}/content", json=content_payload)
                if res.status_code == 200:
                    parser = HTMLToTextParser()
                    parser.feed(res.text)
                    raw_text = parser.get_text()
                    raw_text = re.sub(r"\n\s*\n", "\n\n", raw_text)
                    rendered_text = raw_text[:6000] + (
                        "\n...[Page tronquée]" if len(raw_text) > 6000 else ""
                    )
                else:
                    rendered_text = f"Erreur de rendu Chromium (Code {res.status_code})"
            except Exception as e:
                logger.error(f"Erreur rendu Chromium: {e}")
                rendered_text = f"Impossible de charger la page : {e}"

        return f"Contenu extrait de la page ({target}) :\n\n{rendered_text}"
