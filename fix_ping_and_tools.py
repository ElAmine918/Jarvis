import re

# Fix agent.py tool execution newlines
with open("/Users/amine/Code/MyCloud/jarvis/src/agent.py", "r") as f:
    agent_code = f.read()

agent_code = agent_code.replace('yield f"\\n\\n⚙️ *Exécution de {tool_name}...*\\n\\n"', 'yield f"\\n⚙️ *Exécution de {tool_name}...*"')

with open("/Users/amine/Code/MyCloud/jarvis/src/agent.py", "w") as f:
    f.write(agent_code)

# Fix bot.py cmd_ping
with open("/Users/amine/Code/MyCloud/jarvis/src/bot.py", "r") as f:
    bot_code = f.read()

bot_code = bot_code.replace('/test_tiers : 🧪 Ping des backends', '/ping : 🧪 Ping des API')

new_cmd_ping = """async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return
        
    msg = await update.message.reply_text("📡 *Lancement du Ping...*", parse_mode=ParseMode.MARKDOWN)
    
    agent: JarvisAgent = context.bot_data["agent"]
    user_id = update.effective_user.id
    
    # We test the providers directly
    providers = [
        ("Google (Gemini)", "jarvis-gemini"),
        ("Cloud (OpenRouter)", "jarvis-openrouter"),
        ("Local (LM Studio)", "jarvis-mac"),
        ("Local (Ollama)", "jarvis-ollama")
    ]
    
    results = []
    for name, model_id in providers:
        try:
            response = ""
            async for chunk in agent.process_message([{"role": "user", "content": "Réponds uniquement par 'OK'."}], str(user_id), requested_model=model_id):
                response += chunk
            
            if "❌" in response:
                err = response.replace("❌", "").strip()
                results.append(f"🔴 *{name}* : Échec ({err})")
            else:
                results.append(f"🟢 *{name}* : Succès")
        except Exception as e:
            results.append(f"🔴 *{name}* : Erreur ({e})")
            
    final_text = "📊 *DIAGNOSTIC RÉSEAU*\n━━━━━━━━━━━━━━━━━━━━━\n\n" + "\n".join(results)
    await msg.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)"""

bot_code = re.sub(r'async def cmd_test_tiers\(.*?\):.*?    await msg\.edit_text\(final_text, parse_mode=ParseMode\.MARKDOWN\)', new_cmd_ping, bot_code, flags=re.DOTALL)
bot_code = bot_code.replace('CommandHandler("test_tiers", cmd_test_tiers', 'CommandHandler("ping", cmd_ping')

with open("/Users/amine/Code/MyCloud/jarvis/src/bot.py", "w") as f:
    f.write(bot_code)
