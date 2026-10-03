import re

with open("/Users/amine/Code/MyCloud/jarvis/src/bot.py", "r") as f:
    bot_code = f.read()

# Fix the signature format: response += f"\\n\\n— {backend_used}"
bot_code = bot_code.replace('response += f"\\n\\n_— ⚡️ {backend_used}_"', 'response += f"\\n\\n— {backend_used}"')

# Update cmd_help
help_msg = """    msg = (
        "💡 <b>COMMANDES JARVIS</b>\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "/silent &lt;texte&gt; : Question sans contexte\\n"
        "/reset : 🧹 Efface l'historique\\n"
        "/status : 📊 Bilan matériel\\n"
        "/backend : 🤖 Routage Neural (modèles dispo)\\n"
        "/test_tiers : 🧪 Ping des backends\\n"
        "/skills : Compétences\\n"
        "/show : Affiche/masque le modèle\\n"
        "/help : Ce menu"
    )"""
bot_code = re.sub(r'    msg = \(\n        "💡 <b>GUIDE DES COMMANDES JARVIS.*?    \)', help_msg, bot_code, flags=re.DOTALL)


# Rewrite cmd_backend entirely
new_backend = """async def cmd_backend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return

    from .router import _dead_models
    import time
    
    agent: JarvisAgent = context.bot_data["agent"]
    
    # We call get_all_backends locally to see the pool (without history)
    from .router import get_all_backends
    pool = await get_all_backends(history=[])
    
    current_time = time.time()
    dead_str = ""
    for m, t in _dead_models.items():
        if t > current_time:
            rem = int((t - current_time) / 60)
            dead_str += f"- {m} (bloqué {rem}m)\\n"
            
    if not dead_str:
        dead_str = "Aucun modèle bloqué."
        
    active_str = ""
    for b in pool:
        active_str += f"- {b[2]}\\n"
        
    if not active_str:
        active_str = "Aucun modèle disponible."

    msg = (
        "🤖 *NEURAL ROUTER STATUS*\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        f"*Modèles Disponibles :*\\n{active_str}\\n"
        f"*Circuit Breaker :*\\n{dead_str}\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        f"ℹ️ *Dernier modèle utilisé* : `{getattr(agent, 'last_backend_used', 'Inconnu')}`"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)"""

bot_code = re.sub(r'async def cmd_backend\(.*?\):.*?    \)', new_backend, bot_code, flags=re.DOTALL)

with open("/Users/amine/Code/MyCloud/jarvis/src/bot.py", "w") as f:
    f.write(bot_code)
