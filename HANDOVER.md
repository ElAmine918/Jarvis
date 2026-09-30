# 📘 DOCUMENT DE PASSATION TECHNIQUE (HANDOVER) — PROJET JARVIS / MYCLOUD

> **Destinataire :** Prochain agent IA / Développeur prenant en charge le projet.  
> **Date de rédaction :** 30 Septembre 2026 (Local time 2026-09-29T23:09-04:00)  
> **Dépôt Git :** `ElAmine918/MyCloud` (branche `main`)  
> **Auteur :** Antigravity (Google DeepMind Advanced Agentic Coding)

---

## 1. 🏗️ Architecture Globale & Matériel

Le projet **Jarvis / MyCloud** est un assistant agentique personnel autonome hébergé sur une infrastructure hybride (On-Premise + Cloud).

```
                      ┌──────────────────────────────────────────────┐
                      │                 INTERNET                     │
                      └───────▲──────────────────────────────▲───────┘
                              │                              │
                    Telegram / Webhook             OpenRouter / Gemini
                              │                              │
                              ▼                              ▼
┌──────────────────────────────────────────────┐   ┌───────────────────────────┐
│     TOSHIBA LAPTOP (Serveur Proxmox VE)      │   │     MAC M4 (Machine Dev)  │
│  IP LAN: 192.168.2.100 (SSH alias: pve)      │   │  Tailscale: 100.115.108.9 │
│  CPU: Intel i7-4700MQ (4C/8T) | 16 GB DDR3   │   │  LM Studio (Port 1234)    │
│                                              │   └─────────────▲─────────────┘
│  ┌────────────────────────────────────────┐  │                 │
│  │ LXC 100 (docker-host, Ubuntu 24.04)    │  │                 │
│  │ IP LAN: 192.168.2.76                   │  │                 │
│  │ Tailscale: 100.122.16.8                │◄─┴─────────────────┘
│  │ Path: /app                             │      Tailscale Mesh Net
│  │                                        │
│  │  [Docker Services]                     │
│  │  ├─ jarvis (Port 8080)                 │
│  │  ├─ chromium (Browserless Headless)    │
│  │  ├─ ollama (Port 11434, qwen2.5:7b)    │
│  │  ├─ docker-proxy (Socket sécurisé)     │
│  │  ├─ open-webui (Port 3000)             │
│  │  └─ caddy (Reverse Proxy 80/443)       │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 1.1. Les Machines
1. **Serveur Hôte Proxmox (Toshiba)** :
   - IP LAN : `192.168.2.100` (accessible via `ssh pve` configuré dans `~/.ssh/config` du Mac).
   - CPU : Intel Core i7-4700MQ (Haswell, 4 cœurs physiques / 8 threads logiques).
   - RAM : 16 Go DDR3 double canal.
   - Rôle : Héberge le conteneur LXC 100 sous Proxmox VE 8.
2. **Conteneur LXC 100 (`docker-host`)** :
   - IP LAN : `192.168.2.76`
   - IP Tailscale : `100.122.16.8`
   - OS : Ubuntu 24.04 LTS (Nesting activé `nesting=1`, `keyctl=1`).
   - Répertoire du projet : `/app` (contient `docker-compose.yml`, `.env`, `jarvis/`, `data/`).
3. **Machine de Développement (Mac M4)** :
   - IP Tailscale : `100.115.108.9`
   - Rôle : Machine de dev locale + Fournisseur d'inférence LLM haute vitesse quand elle est allumée via LM Studio (port `1234`).

---

## 2. ⚡ Procédure d'Accès & Commandes Déploiement

### 2.1. Exécuter une commande sur le conteneur LXC
Ne jamais tenter d'accéder au socket Proxmox sans passer par `ssh pve` :
```bash
# Exécution directe via Proxmox pct
ssh pve "pct exec 100 -- <votre-commande>"

# Exemple : voir les conteneurs Docker en cours d'exécution
ssh pve "pct exec 100 -- docker ps"

# Exemple : voir les logs récents de Jarvis
ssh pve "pct exec 100 -- docker logs jarvis --tail 50 -f"
```

### 2.2. Déploiement du code (Live Mount & Hot Restart)
> [!IMPORTANT]
> Dans `/app/docker-compose.yml`, le volume `./jarvis/src:/app/src:ro` est monté en direct !
> Il n'est donc **PAS NÉCESSAIRE** de reconstruire l'image Docker (`docker compose build`) à chaque modification de code Python.

Pour déployer un fichier modifié depuis le Mac vers le serveur :
```bash
# Exemple pour pousser un fichier ou le dossier src complet :
tar -czf update.tar.gz -C /Users/amine/Code/MyCloud jarvis/src && \
scp update.tar.gz pve:/tmp/ && \
ssh pve 'pct push 100 /tmp/update.tar.gz /tmp/update.tar.gz && \
         pct exec 100 -- bash -c "tar -xzf /tmp/update.tar.gz -C /app && rm /tmp/update.tar.gz && cd /app && docker compose restart jarvis"' && \
rm update.tar.gz
```

---

## 3. 🧠 Cascade Multi-Backend & Routage Intelligent

Jarvis utilise une cascade de repli (fallback) ultra-résiliente ordonnée dans [`jarvis/src/router.py`](file:///Users/amine/Code/MyCloud/jarvis/src/router.py) et orchestrée dans [`jarvis/src/agent.py`](file:///Users/amine/Code/MyCloud/jarvis/src/agent.py).

### 3.1. Ordre de Priorité
| Tier | Backend | Endpoint | Modèle | Type | Caractéristiques |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **Mac M4 (LM Studio)** | `http://100.115.108.9:1234/v1` | `qwen/qwen3.5-9b` | Local LAN | Ultra-rapide (>40 tok/s), 0 latence cloud. Actif uniquement quand le Mac est allumé. Détection timeout 1.5s. |
| **Tier 2** | **OpenRouter Cloud** | `https://openrouter.ai/api/v1` | `qwen/qwen3.8-27b:free` | Cloud (Free) | Puissant (27B), supporte le Function Calling, 0 coût, utilise la clé OpenRouter configurée. |
| **Tier 3** | **Google Gemini** | Direct API / OpenAI wrapper | `gemini-2.5-flash` | Cloud (Free tier) | Haute vitesse, grand contexte (1M tokens). |
| **Tier 4** | **Toshiba SLM (Ollama)** | `http://ollama:11434/v1` | `qwen2.5:7b` | Local Proxmox | Filet de sécurité 100% autonome hors-ligne si Internet coupe ou si le Mac est éteint. |

### 3.2. Règle d'Or Utilisateur : Pas de Signature dans le Chat Telegram
> [!CAUTION]
> **Interdiction Formelle :** Ne JAMAIS ajouter de mention du type `— ⚡️ Répondu via Mac M4` ou `Modèle utilisé : ...` à la fin des messages Telegram de l'agent.  
> L'utilisateur veut une expérience conversationnelle propre et naturelle.  
> La télémétrie du backend et du modèle utilisé est **strictement réservée au Dashboard d'Administration** (`http://192.168.2.76:8080/admin`) et à la base SQLite (`/app/data/memory.db`).

---

## 4. ⚙️ Subtilité Matérielle CPU : Le Goulot Toshiba (i7-4700MQ)

L'utilisateur a remarqué lors des tests que seuls 4 cœurs étaient à 100% dans Proxmox et s'est interrogé sur un bridage. Voici l'analyse technique exacte à retenir :

1. **Architecture Haswell** : Le Core i7-4700MQ dispose de **4 cœurs physiques** et de **8 cœurs logiques (Hyper-Threading / SMT)**.
2. **Goulot d'Étranglement Mémoire (Memory Bandwidth Bound)** :
   - L'inférence locale d'un LLM 7B quantifié en Q4_K_M nécessite de charger ~4.7 Go de poids depuis la RAM pour **chaque token** généré.
   - La bande passante théorique maximale de la DDR3 double-canal est de ~18-20 Go/s.
   - Vitesse max théorique = `18 Go/s / 4.7 Go ≈ 3.8 à 5.3 tokens/s`.
3. **Hyper-Threading vs Cœurs Physiques** :
   - Les benchmarks réels ont prouvé que 4 threads physiques ou 8 threads logiques donnent rigoureusement la même vitesse (5.32 tokens/s).
   - L'Hyper-Threading partage le cache L1/L2 et la bande passante du contrôleur mémoire. Lancer 8 threads ne génère aucun gain et augmente la contention de cache.
   - `OLLAMA_NUM_THREADS: 8` a néanmoins été configuré dans `docker-compose.yml` pour satisfaire la planification sur l'ensemble des cœurs logiques.

---

## 5. 🌐 Navigation Web Autonome (Browserless Chromium)

### 5.1. Fonctionnement
- **Conteneur :** `ghcr.io/browserless/chromium:latest` connecté sur le réseau `jarvis-net`.
- **Fichier de l'outil :** [`jarvis/src/tools/browser_tool.py`](file:///Users/amine/Code/MyCloud/jarvis/src/tools/browser_tool.py)
- **Tool name :** `browse_internet`

### 5.2. Subtilités & Contraintes Utilisateur
1. **PAS DE SCREENSHOTS DANS TELEGRAM :**
   - L'utilisateur a explicitement demandé de ne pas recevoir de captures d'écran sur Telegram.
   - L'outil a été modifié pour extraire et retourner uniquement le texte visible et le DOM propre nettoyé (scripts, styles et balises superflues supprimées).
2. **Protection Anti-Bot / CAPTCHA :**
   - Google Search bloque parfois les requêtes automatisées (`IP captcha`).
   - L'outil privilégie la navigation directe vers l'URL (ex: Wikipedia, GitHub, documentation) ou l'extraction de page rendue.

---

## 6. 📱 Bot Telegram & Interface Admin

### 6.1. Bot Telegram (`jarvis/src/bot.py`)
- Développé avec `python-telegram-bot` v20 (asynchrone).
- **Menu natif de commandes** enregistré automatiquement via l'API Telegram (`post_init` hook avec `BotCommand`) :
  - `/status` : Diagnostic immédiat (CPU, RAM, état des 4 conteneurs, backends actifs avec indicateurs colorés 🟢/🔴).
  - `/backend` : Ordre et état de santé de la chaîne de repli.
  - `/skills` : Liste des capacités actives (Docker, Shell système, Chromium, Mémoire).
  - `/help` : Manuel d'utilisation complet.
- **Sécurité :** Filtrage strict par `ALLOWED_TELEGRAM_USER_IDS` dans `.env`.

### 6.2. Dashboard d'Administration (`jarvis/src/admin_ui.py`)
- Accessible sur : `http://192.168.2.76:8080/admin`
- Endpoint API de données : `http://192.168.2.76:8080/admin/api/data`
- Interface Web moderne Vue.js 3 + Tailwind CSS :
  - Badges de statut en direct des 4 backends (LM Studio, OpenRouter, Gemini, Ollama).
  - Monitoring CPU & RAM en temps réel.
  - Historique complet des conversations et des appels d'outils (`browse_internet`, `docker_exec`, etc.).
  - Indication précise de la machine et du modèle ayant répondu à chaque requête.

### 6.3. Open WebUI & Modèles Exposés (`jarvis/src/api.py`)
- Accessible sur : `http://192.168.2.76:3000` (ou via Tailscale `http://100.122.16.8:3000`)
- Endpoint OpenAI : `http://jarvis:8080/v1`
- Modèles disponibles dans le sélecteur d'Open WebUI (`/v1/models`) :
  - `jarvis-auto` : Cascade complète et dynamique (Tier 1 -> Tier 2 -> Tier 3 -> Tier 4).
  - `jarvis-openrouter` (alias `jarvis-omniroute`) : Routage direct vers le backend OpenRouter Cloud (`qwen/qwen3.8-27b:free`).
  - `jarvis-gemini` : Routage direct vers Google Gemini Flash (`gemini-2.0-flash`).
  - `jarvis-ollama` : Routage direct vers Ollama local Toshiba (`qwen2.5:7b`).
  - `jarvis-mac` : Routage direct vers LM Studio sur le Mac M4 (`qwen/qwen3.5-9b`).

---

## 7. 🔒 Sécurité & Docker Socket Proxy

Pour empêcher l'agent ou un conteneur compromis de prendre le contrôle de l'hôte Proxmox :
1. **Pas de montage direct de `/var/run/docker.sock` dans Jarvis.**
2. Jarvis communique via HTTP avec le conteneur `docker-proxy` (`tecnativa/docker-socket-proxy`) sur le réseau interne `docker-proxy-net`.
3. Le proxy n'autorise que les actions déclarées sûres (`CONTAINERS=1`, `POST=1` restreint) et interdit l'accès aux volumes hôtes ou aux options sensibles.
4. Les conteneurs critiques possèdent le label `jarvis.manageable=false` empêchant l'agent de les arrêter ou de les supprimer.

---

## 8. 🐛 Pièges Rencontrés & Résolus (À ne pas reproduire)

1. **Scoping de `b_model` dans `agent.py` :**
   - *Bug :* `b_name` et `model` étaient des variables de boucle dans `for b_name, client, model in backends:`. Lors d'une réponse directe sans boucle supplémentaire, l'accès à `b_model` en fin de fonction levait un `NameError`.
   - *Solution :* Deux variables globales de tour `current_backend = ""` et `current_model = ""` sont initialisées avant la cascade et mises à jour lors de la sélection du backend.
2. **Redirection infinie sur la console Groq sous Brave :**
   - *Cause :* Le bouclier Brave Shields bloque les cookies d'authentification tiers Clerk / Auth0.
   - *Solution :* Désactiver Brave Shields (icône lion dans la barre d'adresse) sur `groq.com`.
3. **Clé API OpenRouter :**
   - La clé a été configurée dans `/app/.env` : `OPENROUTER_API_KEY=sk-or-v1-...`.
   - Modèle utilisé : `qwen/qwen3.8-27b:free`.

---

## 9. 🚀 Guide de Dépannage Rapide

| Symptôme | Cause Probable | Action Corrective |
| :--- | :--- | :--- |
| **Telegram ne répond pas** | Conteneur Jarvis arrêté ou crash token | `ssh pve "pct exec 100 -- docker restart jarvis"` puis vérifier `docker logs jarvis`. |
| **Jarvis répond lentement (>15s)** | Mac M4 éteint et fallback sur Ollama local Toshiba | Normal (inférence CPU à 5.3 tok/s). Si OpenRouter est actif, vérifier les quotas de l'API gratuite. |
| **Erreur de permission Docker** | Tentative de manipulation directe du socket | Utiliser uniquement `DOCKER_HOST="tcp://docker-proxy:2375"`. |
| **Mise à jour de code non prise en compte** | Fichier modifié sur le Mac mais pas poussé sur LXC 100 | Lancer le script de push tarball et `docker compose restart jarvis`. |
