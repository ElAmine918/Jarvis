# MyCloud — Jarvis AI Agent

Agent IA personnel accessible via Telegram, hébergé sur un homelab Proxmox.  
Jarvis peut exécuter des commandes, gérer des containers Docker, naviguer sur le web, et apprendre de nouvelles procédures.

## Architecture

```text
┌────────────────────────────────────────────────┐
│          PROXMOX VE 9 (Bare Metal)             │
│          Toshiba i7-4700MQ — 16 GB RAM         │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │    LXC Container : docker-host           │  │
│  │    Ubuntu 24.04 — Docker Engine          │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐  │  │
│  │  │  jarvis     browser    caddy       │  │  │
│  │  │  (agent)    (headless) (proxy)     │  │  │
│  │  │     │                              │  │  │
│  │  │     ▼                              │  │  │
│  │  │  Telegram ◄──── Toi                │  │  │
│  │  └────────────────────────────────────┘  │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐  │  │
│  │  │  Tes projets (chess, apps, etc.)   │  │  │
│  │  └────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  Tailscale : accès distant chiffré             │
└────────────────────────────────────────────────┘
```

## Stack

| Composant | Techno |
|-----------|--------|
| Hyperviseur | Proxmox VE 9 |
| Container | LXC (Ubuntu 24.04) |
| Runtime | Docker + Docker Compose |
| Agent IA | Python (asyncio) + Claude API |
| Interface | Telegram Bot |
| Browser | Chromium headless (browserless) |
| Reverse proxy | Caddy |
| Réseau distant | Tailscale |

## Démarrage rapide

### 1. Préparer le serveur Proxmox

```bash
# Sur le Proxmox — créer le container LXC
chmod +x setup/create-lxc.sh
./setup/create-lxc.sh

# Dans le LXC — installer Docker + Tailscale
chmod +x setup/install-docker.sh
./setup/install-docker.sh
```

### 2. Configurer et lancer Jarvis

```bash
# Cloner le repo dans le LXC
git clone https://github.com/ElAmine918/MyCloud.git
cd MyCloud

# Configurer les secrets
cp .env.example .env
nano .env  # Remplir TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY, etc.

# Lancer
docker compose up -d
docker compose logs -f jarvis
```

### 3. Parler à Jarvis

Ouvre Telegram, trouve ton bot, et envoie `/start`.

## Structure du projet

```text
MyCloud/
├── docker-compose.yml           # Stack Jarvis (agent + browser + proxy)
├── docker-compose.projects.yml  # Tes projets perso
├── Caddyfile                    # Config reverse proxy
├── .env.example                 # Template variables d'environnement
├── jarvis/                      # Code source de l'agent
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py              # Point d'entrée
│       ├── bot.py               # Bot Telegram
│       ├── agent.py             # Logique agent + tool calling
│       ├── router.py            # Routeur de modèles (cheap → smart → heavy)
│       ├── memory.py            # Système de mémoire / apprentissage
│       └── tools/               # Outils (shell, docker, fichiers, browser)
├── setup/                       # Scripts d'installation Proxmox/LXC
│   ├── create-lxc.sh
│   ├── install-docker.sh
│   └── README.md
└── workspace/                   # Dossier partagé pour les projets
```

## Créer le bot Telegram

1. Parle à [@BotFather](https://t.me/BotFather) sur Telegram
2. `/newbot` → choisis un nom et un username
3. Copie le token dans `.env` → `TELEGRAM_BOT_TOKEN`
4. Parle à [@userinfobot](https://t.me/userinfobot) pour récupérer ton User ID
5. Ajoute ton ID dans `.env` → `ALLOWED_TELEGRAM_USER_IDS`

## Licence

Projet personnel — usage privé.
