# Jarvis — Assistant IA Agentique

> Un assistant IA auto-hébergé et hautement autonome fonctionnant sur Docker. Jarvis est un agent IA multi-backends avec une bascule automatique (failover cascade), une mémoire avancée (PostgreSQL + pgvector), et de pleines capacités DevOps (Docker, Git, Shell).

---

## 🌟 Présentation

Jarvis agit comme un gestionnaire d'infrastructure autonome, un chercheur, et un assistant du quotidien. En interagissant avec Jarvis via **Telegram** ou **Open WebUI**, vous pouvez lui demander de déployer du code, chercher sur le web, gérer vos conteneurs Docker, ou synthétiser des documents grâce à son système RAG avancé (Retrieval-Augmented Generation).

### Fonctionnalités Clés
- **Cascade LLM à 4 Niveaux :** Bascule automatiquement des API cloud (Gemini/OpenRouter) vers des LLM locaux (Ollama/LM Studio) si internet coupe ou si une API impose des limites.
- **Mémoire RAG Avancée :** Utilise PostgreSQL avec l'extension `pgvector` pour une recherche hybride sémantique sur vos anciennes conversations et documents.
- **Capacités DevOps :** Peut lire des logs, exécuter des commandes shell, gérer des dépôts Git, et contrôler des conteneurs Docker.
- **Validation Humaine (Human-in-the-Loop) :** Les actions critiques (comme modifier des conteneurs ou des changements système destructeurs) envoient une demande d'approbation sur Telegram sous forme de boutons interactifs.
- **Consensus Multi-Agents :** Capable de générer un panel de sous-agents pour débattre de problèmes complexes et synthétiser une réponse finale.
- **Capacités Vocales :** Supporte le Speech-to-Text et le Text-to-Speech via des modèles locaux ou le cloud.

## 🏗️ Architecture

```text
                     ┌────────────────────────────────┐
                     │           INTERNET             │
                     └──────▲─────────────────▲───────┘
                            │                 │
                  Telegram / HTTPS    OpenRouter / Gemini APIs
                            │                 │
                            ▼                 ▼
┌───────────────────────────────────────────────────────────┐
│                    SERVEUR DOCKER                         │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Stack Docker Compose                                │  │
│  │                                                     │  │
│  │  ├─ jarvis          (Agent IA Principal, :8080)     │  │
│  │  ├─ jarvis-live     (Agent Vocal LiveKit)           │  │
│  │  ├─ jarvis-pgvector (PostgreSQL + Mémoire Vectoriel)│  │
│  │  ├─ open-webui      (Interface Web de Chat)         │  │
│  │  ├─ caddy           (Reverse Proxy / HTTPS)         │  │
│  │  └─ docker-proxy    (Proxy Socket Sécurisé)         │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

## 🔒 Sécurité & Vie Privée

- **Personnalité Privée :** La personnalité de l'agent est entièrement pilotée par le fichier `data/system_prompt.txt`. Ce fichier est intentionnellement ignoré par Git (`.gitignore`) pour que vous puissiez donner à votre assistant une personnalité très intime sans qu'elle ne fuite sur les dépôts publics.
- **Sécurité du Socket Docker :** Jarvis n'a pas un accès brut au socket `/var/run/docker.sock`. Toutes les commandes passent par un conteneur isolé `tecnativa/docker-socket-proxy`.
- **Sandbox Système :** Jarvis est restreint en lecture et écriture uniquement au dossier `/app/workspace/`.
- **Approbations Interactives :** Les actions destructrices nécessitent votre accord explicite sur Telegram.

## 🚀 Démarrage Rapide

### 1. Prérequis
- Un serveur compatible Docker (Linux/Mac/Proxmox)
- Un token de bot Telegram (obtenu via [@BotFather](https://t.me/BotFather))
- Vos clés API (Gemini, OpenRouter, etc.)

### 2. Installation
Clonez le dépôt et préparez votre environnement :

```bash
git clone https://github.com/VotreUtilisateur/Jarvis.git
cd Jarvis

# Configurez vos variables d'environnement
cp .env.example .env  # (Créez ce fichier et ajoutez-y vos clés)
nano .env

# Configurez la personnalité de l'agent (ce fichier reste privé)
mkdir -p data
echo "Tu es un assistant IA extrêmement efficace et concis." > data/system_prompt.txt
```

### 3. Lancement
```bash
docker compose up -d --build
```

### 4. Utilisation
- **Telegram :** Envoyez `/start` à votre bot.
- **Interface Web :** Naviguez vers `http://ip-de-votre-serveur:3000` (ou votre domaine géré par Caddy).

## 📁 Structure du Projet

```text
Jarvis/
├── docker-compose.yml     # L'orchestration des conteneurs
├── Dockerfile             # Instructions de construction de l'agent
├── Caddyfile              # Configuration du reverse proxy
├── requirements.txt       # Dépendances Python
├── src/jarvis/            # Code applicatif principal
│   ├── core/              # Routage LLM, Logique de l'agent, Config
│   ├── interfaces/        # API, Bot Telegram, Gestion vocale
│   ├── storage/           # Mémoire PostgreSQL & Logs SQLite
│   └── tools/             # Les différents outils (+ de 18) de l'agent
├── db/                    # Schémas PostgreSQL
├── tests/                 # Suite de tests Pytest
└── scripts/               # Scripts shell (sauvegardes, etc.)
```

## 🛠️ Développement & Extension

Jarvis est codé en Python standard (FastAPI). Ajouter un nouvel outil est aussi simple que de créer un nouveau fichier dans `src/jarvis/tools/` qui hérite de `Tool` et qui s'enregistre de lui-même.

Pour lancer les tests localement :
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
PYTHONPATH=src pytest tests/
```

---
**Licence :** MIT
