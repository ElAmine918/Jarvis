# Jarvis — Assistant IA Agentique & Opérateur Homelab

> Un assistant IA personnel et autonome fonctionnant sous Docker. Jarvis combine un routage multi-LLM avec cascade de secours automatique, une mémoire hybride à triple niveau (pgvector + SQLite FTS5), une boucle d'auto-amélioration CI/CD (Self-Coding), une validation humaine interactive (Human-in-the-Loop) et des capacités d'exploitation DevOps complètes (Docker, Proxmox VE, Git).

---

## 🌟 Présentation & Philosophie

Jarvis a été conçu pour être à la fois un **assistant personnel du quotidien** et un **opérateur d'infrastructure autonome**. Connecté à vos interfaces de communication (**Telegram** et **Open WebUI**), il est capable de naviguer sur le web, d'auditer et déployer du code, d'administrer des conteneurs Docker et des machines virtuelles Proxmox, tout en apprenant continuellement de nouvelles compétences.

### Fonctionnalités Clés
- **Cascade LLM à 4 Niveaux & Circuit Breaker :** Sélection intelligente et résiliente parmi plusieurs fournisseurs d'IA (Groq, Gemini, OpenRouter, LM Studio local Mac M4, Ollama local homelab). Bascule automatique et sans coupure en cas de panne réseau ou de dépassement de quota.
- **Auto-Amélioration & Self-Coding (CI/CD) :** L'agent est capable d'écrire de nouveaux outils Python, de les faire auditer par une instance IA de sécurité isolée, de passer les tests de non-régression Pytest et de pousser les modifications directement sur GitHub.
- **Mémoire Hybride Triple Niveau :** 
  - **Vectorielle & RAG sémantique** via PostgreSQL 16 + `pgvector` et Reciprocal Rank Fusion (RRF).
  - **Compétences & Faits** persistants avec recherche plein texte SQLite FTS5.
  - **Rappel opérationnel** des anciennes sessions, des actions d'outils et des statistiques de tokens.
- **Sécurité DevOps & Human-in-the-Loop :** Les commandes Docker passent par un proxy de socket sécurisé et restreint. Toute action potentiellement destructive (extinction de VM Proxmox, arrêt forcé de conteneurs) suspend l'exécution et envoie des boutons d'approbation interactifs sur Telegram.
- **Orchestration Multi-Agents :** Possibilité de déléguer des sous-tâches, de consulter un agent conseiller de niveau supérieur ou de réunir un panel de débat contradictoire (Fusion Panel).
- **Architecture Ouverte MCP (Model Context Protocol) :** Prêt à se connecter dynamiquement aux serveurs MCP externes pour étendre son catalogue d'outils.

---

## 📊 Tableau Comparatif : Jarvis vs Hermes Agent vs OpenClaw

| Dimension | Jarvis | Hermes Agent | OpenClaw |
|---|---|---|---|
| **Canaux d'interaction** | Telegram, Open WebUI, Voix (LiveKit / Whisper / TTS) | 20+ plateformes de messagerie | WhatsApp, Slack, Signal, Discord, Web... |
| **Fiabilité & Routage LLM** | **Cascade dynamique 4 tiers** (Groq/Gemini → Mac local → Ollama homelab) avec Circuit Breaker gradué et routage par complexité | Fournisseur unique configuré à la fois | Fournisseur unique ou bascule basique |
| **Mémoire** | **Triple couche :** RAG hybride pgvector (RRF cosine + Postgres FTS) + Base SQLite FTS5 (`skills`/`facts`) + Recall d'actions | Mémoire curée par l'agent + recherche FTS5 de sessions | Fichiers texte, stockage de sessions persistantes |
| **Apprentissage & Skills** | **Self-Coding CI/CD complet** (code Python généré, audité par IA isolée, testé via Pytest, commité/poussé sur Git) | Création et édition de skills en fichiers Markdown | Skills installables via registre / marketplace |
| **Sécurité Docker** | **Socket Proxy isolé** (`docker-socket-proxy`) + label `jarvis.manageable=true` requis | Accès shell / conteneur direct | Accès conteneur direct ou VM |
| **Contrôle Humain (HITL)** | **Approbations Telegram interactives** (Inline Keyboards bloquants avec timeout) | Confirmations textuelles selon prompts | Selon intégration |
| **Planification** | Rappels persistants SQLite avec reprise après reboot + boucle de veille proactive horaire | Moteur Cron récurrent intégré | Moteur Cron + réveils planifiés |
| **Spécialisation** | **DevOps, Homelab, Proxmox VE & Docker** | Assistant généraliste & recherche | Assistant de vie & messageries |

---

## 🏗️ Architecture du Système

```text
                             ┌─────────────────────────────────┐
                             │            INTERNET             │
                             └────────▲───────────────▲────────┘
                                      │               │
                            Telegram / HTTPS    Cloud APIs (Groq, Gemini, OpenRouter)
                                      │               │
                                      ▼               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             SERVEUR DOCKER (PROXMOX LXC)                         │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │ Réseau Docker (jarvis-net & docker-proxy-net)                              │  │
│  │                                                                            │  │
│  │  ├─ jarvis          (Cœur agentique FastAPI, :8080)                        │  │
│  │  ├─ jarvis-pgvector (PostgreSQL 16 + pgvector, RAG hybride RRF)            │  │
│  │  ├─ open-webui      (Interface utilisateur de chat web)                    │  │
│  │  ├─ caddy           (Reverse Proxy HTTPS automatique)                      │  │
│  │  ├─ docker-proxy    (tecnativa/docker-socket-proxy, socket Docker filtré)  │  │
│  │  ├─ ollama          (LLM local de secours en cas de coupure internet)      │  │
│  │  ├─ chromium        (Navigateur headless pour scraping avec exécution JS)  │  │
│  │  ├─ jarvis-live     (Agent vocal temps-réel LiveKit)                       │  │
│  │  ├─ whisper         (Transcription audio locale)                           │  │
│  │  └─ portainer       (Supervision visuelle des conteneurs)                  │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Cœur Agentique & Résilience Multi-LLM

Le composant [`router.py`](file:///Users/amine/Code/Jarvis/src/jarvis/core/router.py) classe et ordonne dynamiquement les moteurs disponibles selon la complexité du prompt et la disponibilité des endpoints :

1. **Tier 1 (Cloud Rapide & Gratuit) :** Groq (`llama-3.3-70b-versatile`, `mixtral-8x7b`) et OpenRouter (`:free`).
2. **Tier 2 (Raisonnement Cloud Avancé) :** Google Gemini (`gemini-2.5-pro`, `gemini-2.5-flash`, découverte dynamique des modèles).
3. **Tier 3 (Local Puissant via Tailscale) :** LM Studio sur Mac M4 (`qwen2.5-14b-instruct`, `qwen/qwen3.5-9b`).
4. **Tier 4 (Survie Homelab Hors-Ligne) :** Ollama local hébergé dans le LXC (`llama3.2:3b`, `mistral-nemo`).

### Circuit Breaker Gradué
Lorsqu'un backend rencontre une erreur, il est temporairement banni du pool selon la gravité de l'incident :
- **404 Not Found :** Modèle banni définitivement (10 ans).
- **429 Quota journalier :** Banni pendant 24 heures.
- **429 Rate Limit temporaire :** Cooldown de 60 secondes.
- **502/503 Surcharge serveur :** Cooldown de 15 minutes.

---

## 🔄 La Boucle d'Auto-Amélioration (Self-Coding via CI/CD)

Contrairement aux agents limités à la simple lecture d'anciens logs, Jarvis intègre un véritable pipeline d'ingénierie logicielle autonome via l'outil [`SelfImproveTool`](file:///Users/amine/Code/Jarvis/src/jarvis/tools/self_improve.py) :

```text
[Besoin détecté] 
       │
       ▼
[Génération de l'outil Python] ──> Hérite de Tool dans /repo/src/jarvis/tools/
       │
       ▼
[Audit IA de Sécurité Isolé]   ──> Vérification stricte (anti-SSRF, injection, boucle infinie)
       │
  Approuvé ?
   ├── NON ──> Rejet avec rapport détaillé et correction automatique
   └── OUI
       ▼
[Tests de Non-Régression]     ──> Exécution de Pytest (tests de sécurité système)
       │
  Succès ?
   ├── NON ──> Nettoyage et annulation
   └── OUI
       ▼
[Déploiement GitHub Automatique] ──> git add + git commit + git push origin main
```

---

## 🛠️ Registre des Outils (+ de 20 Outils Disponibles)

| Outil | Nom technique | Description |
|---|---|---|
| **Gestion Docker** | `manage_docker` | Supervision (`ps`, `logs`, `inspect`) et contrôle (`start`, `restart`, `stop`) limité aux conteneurs avec le label `jarvis.manageable=true`. |
| **Statut Proxmox** | `proxmox_status` | Récupération en temps réel de l'état des VM QEMU et conteneurs LXC sur le nœud Proxmox. |
| **Action Proxmox (HITL)** | `ask_proxmox_action_approval` | Demande d'approbation sur Telegram avec boutons interactifs pour démarrer/arrêter/redémarrer une VM ou un LXC. |
| **Forçage Docker (HITL)** | `ask_admin_approval` | Demande d'approbation Telegram pour forcer des actions Docker non pré-autorisées. |
| **Fichiers Sécurisés** | `manage_files` | Lecture, écriture, listing et création de répertoires dans les dossiers autorisés (`/app/workspace`, `/app/jarvis/tools`, `/repo`). |
| **Opérations Git** | `git_operations` | Exécution sécurisée de commandes Git sur `/repo` avec allowlist stricte de sous-commandes. |
| **Auto-Amélioration** | `self_improve_pipeline` | Pipeline CI/CD interne : audit de sécurité IA, tests Pytest et push Git automatique. |
| **Interpréteur Python** | `python_interpreter` | Exécution de code Python 3 pour calculs, scripts internes et analyses de données. |
| **Navigation Web** | `browse_internet` | Visite de pages web via Chromium autonome avec rendu JavaScript et protection anti-SSRF. |
| **Lecture Web Rapide** | `read_web_page` | Extraction textuelle nettoyée de pages web publiques avec blocage des réseaux privés et Tailscale. |
| **Actualités** | `search_news` | Recherche en direct sur les flux d'actualités Google News RSS. |
| **Rappels Planifiés** | `schedule_reminder` | Programmation de rappels Telegram différés avec persistance SQLite (survit aux redémarrages). |
| **Mémoire Historique** | `memory_recall` | Recherche dans l'historique des conversations, des actions d'outils et de la consommation de tokens. |
| **RAG Documentaire** | `document_rag_search` | Analyse de documents volumineux et extraction de réponses ciblées. |
| **Délégation Sous-Agent** | `delegate_to_subagent` | Délégation d'une sous-tâche complexe à un agent autonome secondaire. |
| **Conseiller Stratégique** | `consult_advisor` | Consultation d'un modèle supérieur (Gemini Pro) pour validation de raisonnement. |
| **Panel Fusion** | `fusion_panel_analysis` | Débat contradictoire simultané (ex: Gemini + Ollama) avec synthèse par un modèle arbitre. |
| **Métriques Système** | `system_info` | Télémétrie en lecture seule (CPU load, RAM, disque, processus actifs, ports en écoute). |
| **Patch Textuel** | `apply_patch` | Application de modifications chirurgicales dans un fichier existant. |
| **Adaptateur MCP** | `load_mcp_servers` | Intégration dynamique de serveurs d'outils compatibles Model Context Protocol (`mcp_servers.json`). |

---

## 🔒 Sécurité, Sandbox & Recommandations Réseau

### 1. Protection du Socket Docker
Jarvis **n'a jamais accès directement** au socket hôte `/var/run/docker.sock`. Toutes les requêtes transitent par `tecnativa/docker-socket-proxy` qui bloque formellement les opérations sur les volumes, les builds, le réseau de l'hôte et les exécutions de commandes directes (`EXEC=0`).

### 2. Permissions Système & Utilisateur Dédié
Dans le conteneur, l'application tourne sous un utilisateur non-root sans privilèges (**UID/GID 1001** `jarvis`), avec exclusion des capacités Linux (`cap_drop: ALL`, `no-new-privileges: true`).

### 3. Modèle d'Accès Filesystem et Interpréteur Python
- Les opérations de fichiers (`manage_files`) sont strictement cantonnées aux répertoires autorisés : `/app/workspace`, `/app/jarvis/tools` et `/repo`.
- L'outil `python_interpreter` s'exécute dans l'environnement Python du conteneur sans isolation Bubblewrap afin de permettre l'autonomie et le self-coding de l'agent. **Recommandation :** Ne stockez pas de clés ou secrets non chiffrés dans des dossiers lisibles du conteneur en dehors du fichier `.env`.

### 4. Exposition Réseau d'Open WebUI
> [!WARNING]
> Par défaut, l'interface Open WebUI est configurée sans mot de passe local (`WEBUI_AUTH: 'false'`).
> Pour un usage en production :
> - Ne laissez pas le port `3000` exposé publiquement sur Internet.
> - Isolez l'accès derrière un réseau privé (ex: **Tailscale**) ou configurez **Caddy** avec un domaine protégé par HTTPS et authentification basique.

---

## 🚀 Démarrage Rapide

### 1. Prérequis
- Un serveur ou une machine hôte supportant Docker (Linux, LXC Proxmox, Mac M-Series).
- Un bot Telegram créé via [@BotFather](https://t.me/BotFather) avec son token.
- Vos clés d'API (Google AI Studio Gemini, OpenRouter ou Groq).

### 2. Configuration Initiale

```bash
git clone https://github.com/ElAmine918/Jarvis.git
cd Jarvis

# Créer le fichier d'environnement à partir du gabarit
cp .env.example .env
nano .env

# Définir le prompt système et la personnalité (fichier privé ignoré par Git)
mkdir -p data
echo "Tu es Jarvis, l'assistant personnel principal et le confident d'Amine." > data/system_prompt.txt
```

### 3. Lancement des Services

```bash
docker compose up -d --build
```

### 4. Exploitation Quotidienne (`jarvis.sh`)
Pour les déploiements sur Proxmox VE (LXC 100), utilisez le script d'exploitation fourni :
- **Déploiement complet :** `./jarvis.sh deploy`
- **Suivi des logs en direct :** `./jarvis.sh logs`
- **Vérification de l'état des conteneurs :** `./jarvis.sh status`

---

## 💬 Commandes Telegram

- `/status` : Bilan matériel complet (CPU, RAM, Disque, moteur actif).
- `/backend` : Diagnostic du Neural Router (modèles actifs, circuit breaker).
- `/skills` : Liste des compétences et procédures apprises par Jarvis.
- `/ping` : Test de connectivité direct avec chaque fournisseur d'IA.
- `/silent <texte>` : Exécution d'une requête éphémère sans historique.
- `/show` : Activer/désactiver la signature discrète du modèle utilisé.
- `/reset` : Réinitialisation du contexte de conversation.

---

## 📄 Licence

Ce projet est sous licence **MIT**.
