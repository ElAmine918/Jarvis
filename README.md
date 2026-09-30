# Jarvis AI - Autonomous Infrastructure Agent

Jarvis est un agent d'intelligence artificielle autonome conçu pour gérer, superviser et interagir avec l'infrastructure du homelab (serveur Proxmox / Docker). Il est pensé pour être robuste, hautement disponible (système de cascade de LLMs) et hautement sécurisé (Human-in-the-loop et isolation Docker).

## 🌟 Fonctionnalités Principales

*   **Intelligence en Cascade (Haute Disponibilité)** : 
    *   *Tier 1 (Performance)* : Modèle local puissant (Qwen) hébergé sur Mac via LM Studio (réseau Tailscale).
    *   *Tier 2 (Cloud Fallback)* : Gemini 3.5 Flash si le Mac est éteint ou inaccessible.
    *   *Tier 3 (Survie Locale)* : Modèle léger (Llama 3.2 1B) hébergé sur un PC Toshiba local via Ollama si internet est coupé.
*   **Sécurité et Isolation (Docker Socket Proxy)** : Jarvis n'a pas un accès "root" au démon Docker. Il communique via le proxy `tecnativa/docker-socket-proxy` sur un réseau isolé (`docker-proxy-net`), limitant strictement ses actions (lecture, start/stop, pas de suppression ou de création arbitraire). Le conteneur lui-même tourne en *no-new-privileges* avec toutes les capacités Linux retirées (`cap_drop: ALL`).
*   **Human-in-the-loop (Bot Telegram Interactif)** : L'administrateur peut interagir avec Jarvis via un bot Telegram privé. Lorsqu'une action système critique (ex: arrêter le routeur principal) est requise, Jarvis se met en pause et envoie une **demande d'approbation interactive** (boutons Accepter/Refuser) sur Telegram avant d'exécuter l'action brute.
*   **Mémoire Persistante (SQLite)** : Jarvis mémorise automatiquement de nouvelles "skills" (compétences ou contextes spécifiques) qu'il apprend au fil de la conversation.
*   **Accès Web Sécurisé** : Jarvis peut lire des pages web et des dépôts GitHub pour s'informer, avec une protection stricte contre le SSRF (Server-Side Request Forgery) pour l'empêcher de scanner le réseau local interne.

## 🏗️ Architecture

```text
[ Proxmox ] -> [ LXC 100 (Ubuntu) ]
                        |
                        +-- [ Docker ]
                              |-- caddy (Reverse Proxy)
                              |-- open-webui (Interface Web UI)
                              |-- docker-proxy (Filtre Sécurité Docker)
                              |-- jarvis (Cerveau FastAPI / Telegram)
```

## 🛠️ Outils de l'Agent

*   `manage_docker` : Lister, inspecter et redémarrer les conteneurs (autorisés via le label `jarvis.manageable=true`).
*   `ask_admin_approval` : Demander la permission à l'administrateur via Telegram pour exécuter une action Docker interdite en bypassant les labels de sécurité.
*   `system_info` : Récupérer l'état du CPU, de la RAM (via `procps`) et de l'espace disque.
*   `manage_files` : Lire ou écrire des fichiers exclusivement dans son espace de travail isolé (`/app/workspace` et `/app/data/skills`).
*   `read_web_page` : Extraire et parser le contenu texte de sites publics.

## 🚀 Déploiement

### Pré-requis
* Serveur Proxmox avec LXC Ubuntu
* `create-lxc.sh` et `install-docker.sh` (dans le dossier `setup/`)
* Un token de Bot Telegram
* Tailscale (optionnel, pour l'accès aux LLMs locaux déportés)

### Installation
1. Configurer les variables d'environnement dans `/app/.env` :
```env
TELEGRAM_BOT_TOKEN=ton_token
ALLOWED_TELEGRAM_USER_IDS=ton_id_telegram
LM_STUDIO_URL=http://<ip-tailscale>:1234/v1
GEMINI_API_KEY=ta_cle_gemini
OLLAMA_LOCAL_URL=http://ollama:11434/v1
```
2. Compiler et lancer l'agent :
```bash
docker compose build --no-cache jarvis
docker compose up -d
```

## 📱 Utilisation via Telegram

Une fois déployé, contactez votre bot sur Telegram.
*   `/start` : Initie la conversation (seuls les IDs whitelistés sont autorisés).
*   `/status` : Affiche l'état du serveur (CPU, RAM, Uptime).
*   `/backend` : Affiche quel moteur IA (Mac, Gemini ou Toshiba) prend actuellement les commandes.
*   `/skills` : Affiche tout ce que Jarvis a appris et mémorisé de façon permanente.
