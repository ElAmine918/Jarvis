"""
Outil Web Reader sécurisé.
Récupère le contenu texte d'une URL.
Protégé contre les requêtes internes (SSRF).
"""

import ipaddress
import logging
import socket
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class HTMLToTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "meta", "link"):
            self.in_script_or_style = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "meta", "link"):
            self.in_script_or_style = False
        elif tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            self.text.append("\n")

    def handle_data(self, data):
        if not self.in_script_or_style:
            text = data.strip()
            if text:
                self.text.append(text + " ")

    def get_text(self):
        return "".join(self.text).strip()


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


_BLOCKED_HOSTNAMES = {
    "localhost",
    "jarvis",
    "jarvis-live",
    "jarvis-pgvector",
    "docker-proxy",
    "chromium",
    "open-webui",
    "whisper",
    "caddy",
    "portainer",
    "ollama",
}


def _is_safe_url(url: str) -> bool:
    """Vérifie que l'URL a un schéma http ou https valide et n'accède à aucune ressource locale/privée (SSRF)."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower().strip("[]")
        if not hostname:
            return False

        if hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
            return False

        # Vérification si c'est directement une adresse IP (IPv4 ou IPv6)
        if _is_private_ip(hostname):
            return False

        # Résolution DNS pour éviter DNS Rebinding vers une IP privée
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_addr = item[4][0]
                if _is_private_ip(ip_addr):
                    return False
        except (socket.gaierror, Exception):
            # Si le domaine ne peut pas être résolu, on rejette par sécurité
            return False

        return True
    except Exception:
        return False


class WebReaderTool(Tool):
    @property
    def name(self) -> str:
        return "read_web_page"

    @property
    def description(self) -> str:
        return (
            "Lit le contenu textuel d'une URL publique (Internet). "
            "Les sites locaux ou privés sont bloqués par sécurité. "
            "Le HTML est nettoyé pour ne renvoyer que le texte."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "url": {
                    "type": "string",
                    "description": "L'URL complète à lire (ex: https://github.com/...).",
                }
            },
            "required": ["url"],
        }

    async def execute(self, url: str, **kwargs) -> str:
        current_url = url
        max_redirects = 5
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                for _ in range(max_redirects):
                    if not _is_safe_url(current_url):
                        logger.warning(f"Tentative SSRF bloquée vers {current_url}")
                        return "🚫 URL bloquée. Les adresses IP locales, privées, et Tailscale sont interdites."
                    response = await client.get(current_url)
                    if getattr(response, "is_redirect", False) is True:
                        location = response.headers.get("location")
                        if not location or not isinstance(location, str):
                            break
                        current_url = str(httpx.URL(current_url).join(location))
                    else:
                        break
                response.raise_for_status()

            parser = HTMLToTextParser()
            parser.feed(response.text)
            text = parser.get_text()

            # Nettoyer les sauts de ligne multiples
            import re

            text = re.sub(r"\n\s*\n", "\n\n", text)

            # Tronquer pour ne pas inonder le contexte du modèle
            if len(text) > 8000:
                return text[:8000] + "\n...[Contenu tronqué]"
            return text or "⚠️ La page ne contient pas de texte lisible."

        except Exception as e:
            return f"❌ Erreur lors de la lecture : {e}"


class NewsSearchTool(Tool):
    @property
    def name(self) -> str:
        return "search_news"

    @property
    def description(self) -> str:
        return (
            "Recherche les actualités et nouvelles récentes en direct sur un sujet, pays ou mot-clé (ex: 'canada', 'ia', 'france'). "
            "Renvoie les titres et dates des articles d'actualité les plus récents."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Le sujet ou pays dont on cherche les actualités récentes (ex: 'canada', 'technologie', 'montreal').",
                }
            },
            "required": ["query"],
        }

    async def execute(self, query: str, **kwargs) -> str:
        import urllib.parse
        import xml.etree.ElementTree as ET

        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=fr&gl=CA&ceid=CA:fr"

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(url)
                res.raise_for_status()

            root = ET.fromstring(res.content)
            items = root.findall(".//item")
            if not items:
                return f"Aucune actualité trouvée pour '{query}'."

            lines = [f"📰 Actualités récentes pour '{query}' :\n"]
            for item in items[:6]:
                title = (
                    item.find("title").text
                    if item.find("title") is not None
                    else "Sans titre"
                )
                pub_date = (
                    item.find("pubDate").text
                    if item.find("pubDate") is not None
                    else ""
                )
                lines.append(f"• {title} ({pub_date})")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ Erreur recherche actualités : {e}"
