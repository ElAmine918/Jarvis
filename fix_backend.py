import re

with open("/Users/amine/Code/MyCloud/jarvis/src/bot.py", "r") as f:
    bot_code = f.read()

new_backend = """async def cmd_backend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return

    from .router import _dead_models
    import time
    
    agent: JarvisAgent = context.bot_data["agent"]
    from .router import get_all_backends
    pool = await get_all_backends(history=[])
    
    current_time = time.time()
    
    # Comptage des modèles bloqués
    dead_count = sum(1 for t in _dead_models.values() if t > current_time)
    
    # Groupement des modèles disponibles
    gemini = [b[2] for b in pool if "Gemini" in b[0]]
    openrouter = [b[2] for b in pool if "OpenRouter" in b[0]]
    local = [b[2] for b in pool if "LM Studio" in b[0] or "Ollama" in b[0]]
    
    top_model = pool[0][2] if pool else "Aucun"
    
    msg = (
        "🤖 *NEURAL ROUTER*\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        f"☁️ *Gemini* : {len(gemini)} modèles\\n"
        f"🌐 *OpenRouter* : {len(openrouter)} modèles\\n"
        f"🖥️ *Local* : {len(local)} modèles\\n\\n"
        f"🛡️ *Circuit Breaker* : {dead_count} bloqué(s)\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        f"🏆 *Tête de liste* : `{top_model}`\\n"
        f"ℹ️ *Dernier utilisé* : `{getattr(agent, 'last_backend_used', 'Inconnu')}`"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)"""

bot_code = re.sub(r'async def cmd_backend\(.*?\):.*?    await update\.message\.reply_text\(msg, parse_mode=ParseMode\.MARKDOWN\)', new_backend, bot_code, flags=re.DOTALL)

with open("/Users/amine/Code/MyCloud/jarvis/src/bot.py", "w") as f:
    f.write(bot_code)
