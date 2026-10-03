import asyncio
import logging
import httpx
import subprocess
from .config import TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_USER_IDS

logger = logging.getLogger(__name__)

async def proactive_monitoring_loop():
    """Vérifie l'état des conteneurs toutes les heures et alerte en cas de crash."""
    if not ALLOWED_TELEGRAM_USER_IDS or not TELEGRAM_BOT_TOKEN:
        logger.warning("Monitoring proactif désactivé (pas de token Telegram).")
        return
        
    user_id = ALLOWED_TELEGRAM_USER_IDS[0]
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    logger.info("Boucle de monitoring proactif démarrée.")
    
    while True:
        try:
            await asyncio.sleep(3600)  # Vérification toutes les heures
            
            try:
                # Utilise Docker pour lister les conteneurs plantés
                result = subprocess.run(
                    ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"], 
                    capture_output=True, text=True, timeout=10
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    crashed = []
                    for line in lines:
                        if not line: continue
                        name, status = line.split("|", 1)
                        # On cherche les conteneurs "Exited" mais on ignore ceux qui se sont arrêtés normalement "Exited (0)"
                        if "Exited" in status and "Exited (0)" not in status:
                            crashed.append(name)
                            
                    if crashed:
                        msg = "🚨 **Alerte Proactive : Anomalie Système** 🚨\n\nJ'ai détecté que les conteneurs suivants ont crashé récemment :\n"
                        for c in crashed:
                            msg += f"- `{c}`\n"
                        msg += "\nVeux-tu que j'utilise l'outil Docker pour les redémarrer ?"
                        
                        async with httpx.AsyncClient() as client:
                            await client.post(url, json={
                                "chat_id": user_id, 
                                "text": msg, 
                                "parse_mode": "Markdown"
                            })
                            logger.info(f"Alerte proactive envoyée pour {len(crashed)} conteneurs.")
            except Exception as e:
                logger.error(f"Erreur de diagnostic Docker proactif: {e}")
                
        except asyncio.CancelledError:
            logger.info("Monitoring proactif arrêté.")
            break
        except Exception as e:
            logger.error(f"Erreur dans la boucle de monitoring proactif: {e}")
            await asyncio.sleep(60) # Évite de boucler frénétiquement en cas d'erreur
