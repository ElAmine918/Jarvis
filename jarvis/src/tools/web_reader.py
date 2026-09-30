"""
Outil Web Reader sécurisé.
Récupère le contenu texte d'une URL.
Protégé contre les requêtes internes (SSRF).
"""
import ipaddress
import logging
import socket
from html.parser import HTMLParser
from typing import Any, Dict
from urllib.parse import urlparse

import httpx

from .base import Tool

logger = logging.getLogger(__name__)


class HTMLToTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'head', 'meta', 'link'):
            self.in_script_or_style = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'head', 'meta', 'link'):
            self.in_script_or_style = False
        elif tag in ('p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'):
            self.text.append('\n')

    def handle_data(self, data):
        if not self.in_script_or_style:
            text = data.strip()
            if text:
                self.text.append(text + ' ')

    def get_text(self):
        return "".join(self.text).strip()


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def _is_safe_url(url: str) -> bool:
    """Vérifie que l'URL est http(s) et ne pointe pas vers le réseau local."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # Résoudre l'IP pour contrer les DNS rebinding basiques
        ip_address = socket.gethostbyname(hostname)
        if _is_private_ip(ip_address) or _is_private_ip(hostname): # hostname peut être une IP
            return False
            
        # Bloquer les IP de Tailscale (100.64.0.0/10) explicitement
        ip = ipaddress.ip_address(ip_address)
        if ip in ipaddress.ip_network('100.64.0.0/10'):
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
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "url": {
                    "type": "string",
                    "description": "L'URL complète à lire (ex: https://github.com/...)."
                }
            },
            "required": ["url"]
        }

    async def execute(self, url: str, **kwargs) -> str:
        if not _is_safe_url(url):
            logger.warning(f"Tentative SSRF bloquée vers {url}")
            return "🚫 URL bloquée. Les adresses IP locales, privées, et Tailscale sont interdites."

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
            parser = HTMLToTextParser()
            parser.feed(response.text)
            text = parser.get_text()
            
            # Nettoyer les sauts de ligne multiples
            import re
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            # Tronquer pour ne pas inonder le contexte du modèle
            if len(text) > 8000:
                return text[:8000] + "\n...[Contenu tronqué]"
            return text or "⚠️ La page ne contient pas de texte lisible."
            
        except Exception as e:
            return f"❌ Erreur lors de la lecture : {e}"
