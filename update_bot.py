import re

# Update bot.py
with open("jarvis/src/bot.py", "r") as f:
    bot_code = f.read()

# Inject cmd_show
cmd_show_code = """
async def cmd_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update): return
    
    current = context.user_data.get("show_signature", False)
    context.user_data["show_signature"] = not current
    new_state = context.user_data["show_signature"]
    
    state_str = "ACTIVÉE ✅" if new_state else "DÉSACTIVÉE ❌"
    msg = f"🪧 **Affichage du modèle** : {state_str}\n"
    if new_state:
        msg += "Le nom du modèle sera discrètement affiché à la fin de mes réponses."
    else:
        msg += "Les réponses seront envoyées sans signature."
        
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def handle_message"""

bot_code = bot_code.replace("async def handle_message", cmd_show_code)

# Register command
register_code = """    application.add_handler(CommandHandler("show", cmd_show))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))"""

bot_code = bot_code.replace('    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))', register_code)


# Inject logic in handle_message
handle_msg_logic = """        from .logger_db import log_conversation
        backend_used = getattr(agent, 'last_backend_used', 'Inconnu')
        log_conversation(str(user_id), "telegram", str(user_id), user_text, response, backend_used)
        
        # Ajout de la signature si activée
        show_signature = context.user_data.get("show_signature", False)
        if show_signature:
            # Rendre ça ultra sobre
            response += f"\\n\\n_— ⚡️ {backend_used}_"
            
        # Envoi final du message"""

bot_code = re.sub(
    r"        from .logger_db import log_conversation.*?# Envoi final du message",
    handle_msg_logic,
    bot_code,
    flags=re.DOTALL
)

with open("jarvis/src/bot.py", "w") as f:
    f.write(bot_code)

# Update agent.py to strip new signature
with open("jarvis/src/agent.py", "r") as f:
    agent_code = f.read()

agent_code = agent_code.replace('.split("\\n\\n_— ⚡️ Répondu via")[0]', '.split("\\n\\n_— ⚡️")[0]')

with open("jarvis/src/agent.py", "w") as f:
    f.write(agent_code)

print("Updates applied to bot.py and agent.py locally.")
