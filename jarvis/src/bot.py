import logging
import datetime
import psutil
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from .config import (
    TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_USER_IDS, 
    LM_STUDIO_URL, LM_STUDIO_HEALTH_TIMEOUT,
    OPENROUTER_API_KEY, OPENROUTER_MODEL,
    OLLAMA_LOCAL_URL, OLLAMA_LOCAL_MODEL,
    GEMINI_API_KEY
)
from .agent import JarvisAgent
from .router import check_endpoint

logger = logging.getLogger(__name__)
START_TIME = datetime.datetime.now()


async def _check_allowed(update: Update) -> bool:
    """Vérifie si l'utilisateur est autorisé, sinon bloque et affiche l'ID."""
    user_id = update.effective_user.id
    if not ALLOWED_TELEGRAM_USER_IDS:
        logger.warning(f"Tentative de {user_id} mais ALLOWED_TELEGRAM_USER_IDS est vide.")
        await update.message.reply_text(
            f"🔒 Sécurité activée.\n\nL'accès est bloqué car `ALLOWED_TELEGRAM_USER_IDS` n'est pas configuré dans le fichier `.env`.\n\nTon ID Telegram est : `{user_id}`\n\nAjoute-le dans le fichier `.env` sur le serveur et redémarre Jarvis.",
            parse_mode=ParseMode.MARKDOWN
        )
        return False
    if user_id not in ALLOWED_TELEGRAM_USER_IDS:
        logger.warning(f"Accès refusé pour {user_id}.")
        return False
    return True


async def _send_long(update: Update, text: str):
    """Envoie un message, en le découpant si > 4000 chars. Fallback sans Markdown."""
    for i in range(0, len(text), 4000):
        chunk = text[i:i+4000]
        try:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(chunk)


# --- Handlers ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return
    msg = (
        "👋 *Bienvenue sur Jarvis OS v5.2*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Je suis ton assistant personnel et opérateur d'infrastructure autonome.\n\n"
        "🛠 *Mes Capacités Clés* :\n"
        "• 🌐 *Navigation Web* : J'ouvre des sites en direct via Chromium et j'en extrais le contenu.\n"
        "• 🐳 *Gestion Docker* : Supervision et contrôle de tes conteneurs avec sécurité renforcée.\n"
        "• 🔐 *Human-in-the-Loop* : Pour les actions critiques, je t'envoie des boutons d'approbation ici.\n"
        "• 🧠 *Apprentissage Continu* : Mémorisation de tes préférences et compétences.\n\n"
        "📋 *Commandes Disponibles* :\n"
        "/status — 📊 Rapport complet (CPU, RAM, Disque, Moteur actif)\n"
        "/backend — 🤖 État des 4 tiers d'IA et cascade de secours\n"
        "/skills — 🧠 Consulter les connaissances apprises\n"
        "/help — 💡 Guide rapide d'utilisation\n\n"
        "Tu peux aussi me parler naturellement à tout moment !"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return
    msg = (
        "💡 *GUIDE DES COMMANDES JARVIS*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🗣️ *Conversations & Contexte :*\n"
        "• `/silent <texte>` : Pose une question éphémère (le contexte est ignoré et rien n'est sauvegardé).\n"
        "• `/reset` : 🧹 Efface notre historique immédiat pour repartir de zéro (économise les tokens).\n\n"
        "⚙️ *Monitoring & Moteurs IA :*\n"
        "• `/status` : 📊 Bilan matériel (CPU, RAM, Disque) et état réseau des API (Proxmox/Local).\n"
        "• `/backend` : 🤖 Affiche la cascade IA (Quel modèle va répondre en priorité actuellement).\n"
        "• `/test_tiers` : 🧪 Ping chaque modèle (Mac, OpenRouter, Gemini, Toshiba) pour vérifier leur fonctionnement.\n\n"
        "🧠 *Mémoire & Capacités :*\n"
        "• `/skills` : Affiche les compétences apprises par Jarvis à long terme.\n"
        "• `/help` : Affiche ce menu d'aide.\n\n"
        "💬 *En conversation libre :*\n"
        "Tu peux lui demander directement : _« Liste les conteneurs »_, _« Lance une recherche web »_, _« Lis ce fichier »_ ou _« Invoque un subagent »_ !"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return

    agent: JarvisAgent = context.bot_data["agent"]
    uptime = datetime.datetime.now() - START_TIME
    uptime_str = str(uptime).split('.')[0]
    
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count(logical=True)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    ram_used_gb = round(ram.used / (1024**3), 1)
    ram_total_gb = round(ram.total / (1024**3), 1)
    disk_free_gb = round(disk.free / (1024**3), 1)

    # Vérification des moteurs
    lm_up = await check_endpoint(LM_STUDIO_URL, 1.5)
    ollama_up = await check_endpoint(OLLAMA_LOCAL_URL, 1.5)

    if lm_up:
        active_engine = "🍏 Mac M4 (LM Studio - Qwen 3.5 9B)"
    elif bool(OPENROUTER_API_KEY):
        active_engine = f"🌐 OpenRouter ({OPENROUTER_MODEL})"
    elif bool(GEMINI_API_KEY):
        active_engine = "☁️ Gemini Flash (Google Cloud)"
    elif ollama_up:
        active_engine = f"🦙 Toshiba Local (Ollama - {OLLAMA_LOCAL_MODEL})"
    else:
        active_engine = "🔴 Aucun moteur disponible"

    msg = (
        "📊 *RAPPORT SYSTÈME JARVIS*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Disponibilité* : `{uptime_str}`\n"
        f"💻 *CPU Proxmox* : `{cpu_percent}%` ({cpu_count} cœurs alloués)\n"
        f"🧠 *RAM Utilisée* : `{ram.percent}%` ({ram_used_gb} Go / {ram_total_gb} Go)\n"
        f"💾 *Disque Système* : `{disk.percent}%` ({disk_free_gb} Go libres)\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *Moteur actif* :\n└ {active_engine}\n"
        f"🎯 *Dernière exécution* : `{agent.last_backend_used}`"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_backend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return

    agent: JarvisAgent = context.bot_data["agent"]

    lm_up = await check_endpoint(LM_STUDIO_URL, 2.5)
    ollama_up = await check_endpoint(OLLAMA_LOCAL_URL, 1.5)

    # Statuts détaillés
    t1_status = "🟢 En ligne (`qwen/qwen3.5-9b`)" if lm_up else "🔴 Inaccessible (Mac éteint ou hors Tailscale)"
    t2_status = f"🟢 Actif (`{OPENROUTER_MODEL}`)" if OPENROUTER_API_KEY else "⚪️ Non configuré"
    t3_status = "🟢 Configuré (Clé API active)" if GEMINI_API_KEY else "⚪️ Non configuré"
    t4_status = f"🟢 En ligne (`{OLLAMA_LOCAL_MODEL}` - 8 cœurs)" if ollama_up else "🔴 Inaccessible"

    if lm_up:
        lead = "🍏 *Tier 1 : Mac M4 (LM Studio)* prend la priorité."
    elif OPENROUTER_API_KEY:
        lead = f"🌐 *Tier 2 : OpenRouter ({OPENROUTER_MODEL})* prend le relais (Mac hors-ligne)."
    elif GEMINI_API_KEY:
        lead = "☁️ *Tier 3 : Gemini Flash (Cloud)* prend le relais."
    elif ollama_up:
        lead = "🦙 *Tier 4 : Toshiba (Ollama)* actif en survie locale autonome."
    else:
        lead = "❌ Aucun backend ne répond actuellement."

    msg = (
        "🤖 *ARCHITECTURE DES MOTEURS IA*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ *Tier 1 (Performance - Mac M4)* :\n"
        f"   └ {t1_status}\n\n"
        f"2️⃣ *Tier 2 (Cloud Gratuit - OpenRouter)* :\n"
        f"   └ {t2_status}\n\n"
        f"3️⃣ *Tier 3 (Cloud Fallback - Google Gemini)* :\n"
        f"   └ {t3_status}\n\n"
        f"4️⃣ *Tier 4 (Survie Locale - Toshiba Ollama)* :\n"
        f"   └ {t4_status}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 *Priorité actuelle* :\n{lead}\n\n"
        f"ℹ️ *Dernier modèle utilisé* :\n`{agent.last_backend_used}`"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return
    agent: JarvisAgent = context.bot_data["agent"]
    skills = await agent.memory.search_skills("")
    if not skills:
        await update.message.reply_text("Aucune compétence sauvegardée pour l'instant.")
        return
    lines = ["📚 *Compétences apprises :*\n"]
    for s in skills:
        lines.append(f"• *{s['name']}* — {s['description']} (utilisé {s['use_count']} fois)")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_test_tiers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return
        
    msg = await update.message.reply_text("⏳ *Test fonctionnel des tiers en cours...*", parse_mode=ParseMode.MARKDOWN)
    agent: JarvisAgent = context.bot_data["agent"]
    user_id = update.effective_user.id
    
    tiers = [
        ("Tier 1 (LM Studio)", "jarvis-mac"),
        ("Tier 2 (OpenRouter)", "jarvis-openrouter"),
        ("Tier 3 (Gemini)", "jarvis-gemini"),
        ("Tier 4 (Ollama)", "jarvis-ollama")
    ]
    
    results = []
    for name, model_id in tiers:
        try:
            response = ""
            async for chunk in agent.process_message([{"role": "user", "content": "Réponds uniquement par 'OK'."}], str(user_id), requested_model=model_id):
                response += chunk
            
            if "❌" in response:
                # Extraire juste l'erreur courte
                err = response.replace("❌", "").strip()
                results.append(f"🔴 *{name}* : Échec ({err})")
            else:
                results.append(f"🟢 *{name}* : Succès (Réponse: `{response.strip()}`)")
        except Exception as e:
            results.append(f"🔴 *{name}* : Erreur système ({e})")
            
    final_text = "📊 *RÉSULTAT DES TESTS FONCTIONNELS*\n━━━━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(results)
    await msg.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return
    context.user_data["history"] = []
    await update.message.reply_text("🧹 *Mémoire effacée.* Le contexte de notre conversation a été réinitialisé.", parse_mode=ParseMode.MARKDOWN)

async def cmd_silent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return
        
    user_text = update.message.text.replace("/silent", "", 1).strip()
    if not user_text:
        await update.message.reply_text("⚠️ Ajoute ta demande après la commande, ex: `/silent Quelle est la capitale ?`", parse_mode=ParseMode.MARKDOWN)
        return
        
    user_id = update.effective_user.id
    agent: JarvisAgent = context.bot_data["agent"]
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        response = ""
        # On passe uniquement ce message, avec un faux ID pour ne pas polluer les logs standards si possible
        async for chunk in agent.process_message([{"role": "user", "content": user_text}], session_id=f"silent_{user_id}"):
            response += chunk
            
        if len(response) < 4000:
            try:
                await update.message.reply_text(f"👻 *Réponse éphémère :*\n\n{response}", parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await update.message.reply_text(f"👻 Réponse éphémère :\n\n{response}")
        else:
            await _send_long(update, response)
    except Exception as e:
        logger.error(f"Erreur /silent: {e}")
        await update.message.reply_text("❌ Une erreur interne s'est produite lors de la requête silencieuse.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_allowed(update):
        return

    user_text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "Inconnu"
    
    if not user_text:
        return

    logger.info(f"[TELEGRAM] Message reçu de ID:{user_id} (@{username}) : {user_text}")

    agent: JarvisAgent = context.bot_data["agent"]

    # Maintenir un historique des conversations dans Telegram (max 10 messages)
    if "history" not in context.user_data:
        context.user_data["history"] = []
    
    history = context.user_data["history"]
    history.append({"role": "user", "content": user_text})
    
    # Garder seulement les 10 derniers messages pour éviter de saturer le contexte
    if len(history) > 10:
        history = history[-10:]

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    try:
        response = ""
        
        # Attendre la réponse complète sans streaming ni message d'initialisation
        async for chunk in agent.process_message(history, str(user_id)):
            response += chunk
                    
        history.append({"role": "assistant", "content": response})
        
        from .logger_db import log_conversation
        log_conversation(str(user_id), "telegram", str(user_id), user_text, response, getattr(agent, 'last_backend_used', 'unknown'))
        
        # Envoi final du message
        if len(response) < 4000:
            try:
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await update.message.reply_text(response) # fallback without markdown
        else:
            await _send_long(update, response)
            
    except Exception as e:
        logger.error(f"Erreur traitement message: {e}", exc_info=True)
        history.pop()  # Retirer le message utilisateur qui a échoué
        # M-01 : Ne pas exposer les détails d'erreur internes à l'utilisateur
        await update.message.reply_text("❌ Une erreur interne s'est produite. Réessaie dans un instant.")


def build_app(agent: JarvisAgent) -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN manquant dans .env")

    from telegram import BotCommand

    async def post_init(application: Application):
        commands = [
            BotCommand("status", "📊 Rapport système (CPU, RAM, Disque, Moteur)"),
            BotCommand("backend", "🤖 État des moteurs IA & cascade"),
            BotCommand("skills", "🧠 Compétences et mémoire"),
            BotCommand("test_tiers", "🧪 Test fonctionnel de chaque moteur IA"),
            BotCommand("reset", "🧹 Effacer l'historique de la conversation"),
            BotCommand("silent", "👻 Poser une question éphémère sans contexte"),
            BotCommand("help", "💡 Guide et exemples d'utilisation")
        ]
        try:
            await application.bot.set_my_commands(commands)
        except Exception as e:
            logger.warning(f"Impossible d'enregistrer les commandes Telegram: {e}")
            
        import os
        allowed = [uid.strip() for uid in os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").split(",") if uid.strip()]
        for uid in allowed:
            try:
                await application.bot.send_message(chat_id=uid, text="🔌 *Système en ligne.* Jarvis est réveillé et prêt. Les messages en attente vont être traités.", parse_mode="Markdown")
            except Exception:
                pass

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.bot_data["agent"] = agent

    app.add_handler(CommandHandler("start", cmd_start, block=False))
    app.add_handler(CommandHandler("help", cmd_help, block=False))
    app.add_handler(CommandHandler("status", cmd_status, block=False))
    app.add_handler(CommandHandler("backend", cmd_backend, block=False))
    app.add_handler(CommandHandler("skills", cmd_skills, block=False))
    app.add_handler(CommandHandler("test_tiers", cmd_test_tiers, block=False))
    app.add_handler(CommandHandler("reset", cmd_reset, block=False))
    app.add_handler(CommandHandler("silent", cmd_silent, block=False))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message, block=False))
    app.add_handler(CallbackQueryHandler(handle_callback, block=False))

    return app

from telegram.ext import CallbackQueryHandler
from .approvals import PENDING_APPROVALS, APPROVAL_RESULTS

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Callback answer expiré : {e}")
    
    if not await _check_allowed(update):
        return
        
    data = query.data
    if data.startswith("approve_") or data.startswith("reject_"):
        action, req_id = data.split("_", 1)
        
        if req_id in PENDING_APPROVALS:
            APPROVAL_RESULTS[req_id] = (action == "approve")
            PENDING_APPROVALS[req_id].set()  # Réveille l'outil admin_tool
            
            texte_resultat = "✅ **Action approuvée** et en cours d'exécution..." if action == "approve" else "❌ **Action refusée**."
            try:
                await query.edit_message_text(
                    f"{query.message.text}\n\n{texte_resultat}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
        else:
            try:
                await query.edit_message_text(
                    f"{query.message.text}\n\n⏳ *Demande expirée (timeout).* ",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
