# Référence : Architecture Tools vs Skills (Inspiré de Hermes Agent)

Ce document consigne la liste des **Tools** et **Skills** de l'agent **Hermes (Nous Research)** afin de guider l'évolution de l'architecture de **Jarvis**.

---

## 🧠 Différence Fondamentale : Tool vs Skill

Dans les architectures d'agents modernes :

| Concept | Définition | Exemple | Nature technique |
| :--- | :--- | :--- | :--- |
| **Tool (Outil)** | **Une capacité d'action atomique (Les "Mains")**. Une fonction Python exécutable qui interagit avec le système ou une API externe. | `read_file()`, `execute_code()`, `docker_exec()`, `image_generate()` | Code Python exécutable avec schema JSON (arguments stricts, retour déterministe). |
| **Skill (Compétence)** | **Un savoir-faire méthodologique (Le "Cerveau métier")**. Un ensemble d'instructions, de workflows ou de prompts spécialisés qui orchestrent plusieurs tools pour accomplir une mission complexe. | `email-inbox-triage`, `sdlc-review`, `architecture-diagram`, `claude-code` | Fichier Markdown (instructions, prompt contextuel, règles métier, scripts helpers). |

> **Analogie :** 
> * Le **Tool**, c'est le scalpel, le marteau ou la clé à molette.
> * Le **Skill**, c'est le savoir-faire du chirurgien, du charpentier ou du mécanicien qui sait dans quel ordre utiliser les outils pour résoudre un problème donné.

---

## 🛠️ Hermes Agent — Inventaire des Tools (24 Tools)

Ces outils représentent les primitives d'action dont dispose l'agent :

### 1. Navigation Web & Interaction
* `browser`: `browser_vault_enter_code`, etc. (Contrôle de navigateur headless sécurisé)
* `browser-use`: `browser_exec` (Automatisation de navigation web interactive)
* `web`: `blocked-page-recovery` (Bypass de protections et récupération de contenu web bloqué)

### 2. Système de Fichiers & Code
* `file`: `read_file`, `write_file`, `patch` (modification ciblée par diff), `search_files`
* `code_execution`: `execute_code` (Exécution de scripts Python / Bash en sandbox)

### 3. Orchestration & Multimodal
* `delegation`: `delegate_task` (Délégation de sous-tâches à des sous-agents spécialisés)
* `clarify`: `clarify` (Demande d'informations complémentaires à l'utilisateur)
* `connections`: `manage_connections` (Gestion des sessions et connexions externes)
* `image_gen`: `image_generate` (Génération et retouche d'images)

---

## 📚 Hermes Agent — Inventaire des Skills (54 Skills)

Ces compétences sont regroupées par domaines d'expertise métier :

### 1. Autonomous AI Agents (Orchestration multi-agents)
* `claude-code` : Pilotage de l'outil CLI Claude Code
* `opencode` : Pilotage d'OpenCode pour des refactors massifs
* `codex` : Génération de code automatisée
* `computer-use` : Interaction directe avec le bureau / l'interface graphique
* `hermes-agent` : Auto-récursion et délégation

### 2. Software Development & DevOps
* `codebase-inspection` : Audit et cartographie d'une base de code
* `github` : Gestion des PRs, issues, revues de code
* `sdlc-review` : Revue de cycle de développement logiciel (sécurité, tests, CI/CD)
* `node-inspect-debugger` : Débogage interactif d'applications Node.js
* `dogfood` : Auto-évaluation et tests sur soi-même
* `hermes-agent-skill-authoring` : Capacité de l'agent à créer de nouveaux skills de manière autonome

### 3. Creative & Conception Visuelle
* `architecture-diagram` : Conception de diagrammes d'architecture système (Mermaid / PlantUML)
* `baoyu-infographic` : Génération d'infographies et schémas visuels
* `claude-design` / `design-md` : Conception d'interfaces et de chartes graphiques
* `popular-web-designs` : Modèles de design web modernes
* `manim-video` : Création d'animations mathématiques et graphiques avec Manim
* `p5js` : Programmation visuelle créative
* `ascii-video` : Visualisation en mode texte dans le terminal
* `humanizer` : Réécriture de texte pour un ton plus naturel et percutant

### 4. Productivité & Bureautique
* `google-workspace` : Google Docs, Sheets, Drive
* `notion` : Lecture et mise à jour de bases Notion
* `obsidian` : Organisation de notes et graphes de connaissances Markdown
* `airtable` / `box` : Gestion de bases de données et stockage cloud
* `document-to-action-items` : Transformation de comptes-rendus en plans d'actions
* `meeting-action-items` : Extraction de tâches à partir de réunions
* `docx` / `pdf` / `powerpoint` : Création et manipulation de documents Office et présentations

### 5. Communication & E-mails
* `email-inbox-triage` : Tri automatique, classification et priorisation des e-mails
* `himalaya` : Client e-mail en ligne de commande pour envoyer et lire des mails

### 6. Recherche & Synthèse
* `arxiv` : Recherche et résumé de papiers scientifiques académiques
* `competitor-news-monitor` : Veille concurrentielle et technologique automatisée
* `grounded-citations` : Vérification des faits et sourçage précis
* `llm-wiki` : Construction et interrogation de wikis de connaissances internes

### 7. Multimédia & Médias Sociaux
* `gif-search` : Recherche de GIFs pertinents
* `songsee` / `youtube-content` : Analyse et extraction de contenu vidéo/audio
* `xurl` : Extraction et veille sur les réseaux sociaux (X / Twitter)

---

## 🎯 Feuille de Route d'Intégration pour Jarvis

1. **Phase 1 : Formaliser la distinction dans l'arborescence**
   * Garder `src/jarvis/tools/` pour les **Tools** (les fonctions Python pures : Docker, SSH, Git, Whisper, pgvector).
   * Créer `src/jarvis/skills/` pour les **Skills** (des dossiers avec un fichier `SKILL.md` décrivant la méthode et les prompts système).
2. **Phase 2 : Importer les Skills prioritaires pour Jarvis**
   * `sdlc-review` (Audit automatique avant déploiement Proxmox)
   * `codebase-inspection` (Cartographie de MyCloud / Jarvis)
   * `email-inbox-triage` (Gestion des e-mails via Telegram)
   * `architecture-diagram` (Génération de schémas Mermaid envoyés sur Telegram)
   * `claude-code` / `opencode` (Délégation de gros chantiers de programmation)
