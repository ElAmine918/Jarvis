# Jarvis AI - Assistant Personnel (Sécurisé)

Un agent IA personnel multi-modèles avec tolérance aux pannes (Mac M4 -> Gemini Cloud -> Ollama local).

---

## 🔒 Sécurité et Isolation

La philosophie de sécurité de Jarvis repose sur la **réduction de surface** plutôt que sur le filtrage. L'agent n'a **pas accès à un shell générique**.

### 1. Fichiers (`filesystem.py`)
- L'agent ne peut lire et écrire que dans `/app/workspace`.
- La résolution de chemin utilise `Path.resolve().is_relative_to()`. Il est physiquement impossible de lire `/etc/passwd` ou de remonter l'arborescence avec `../`.
- Les opérations de suppression, déplacement et copie ont été retirées.

### 2. Informations système (`system_info.py`)
- Outil en lecture seule fournissant des métriques (CPU, RAM, processus, ports).
- **Zéro injection possible** : les commandes système (`free`, `df`, `ss`) sont appelées via `create_subprocess_exec` avec des arguments figés dans le code. Les entrées de l'agent servent uniquement à router vers la bonne fonction.

### 3. Gestion Docker (`docker_tool.py`)
- **Action de destruction retirées** : `rm`, `prune`, `compose-up` n'existent pas.
- **Liste blanche par Label** : Jarvis ne peut démarrer, arrêter ou redémarrer que les conteneurs portant explicitement le label Docker `jarvis.manageable=true`. Les conteneurs système (comme Jarvis lui-même ou Open WebUI) rejettent toute tentative d'altération.
- Validation regex stricte du nom du conteneur (`^[a-zA-Z0-9][a-zA-Z0-9_.-]*$`), rejetant les options injectées (`-f`) et les IDs hexadécimaux courts.

### 4. Navigation Web (`browser.py`)
- Le conteneur Chromium (`jarvis-browser`) a été **entièrement retiré** de l'architecture pour prévenir les attaques par injection de prompt via du contenu web hostile. L'agent ne peut plus naviguer sur Internet.

---

## ⚠️ Limites Connues et Travaux Restants

| Décision | Raison |
| :--- | :--- |
| **Accès root potentiel** | Le socket Docker brut (`/var/run/docker.sock`) est encore monté dans le conteneur Jarvis. En cas de vulnérabilité, cela offre un accès root implicite au LXC hôte. Prochaine étape : intégration de `docker-socket-proxy`. |
| **Secrets dans l'environnement** | Les clés d'API (comme Gemini) résident toujours dans les variables d'environnement du processus d'exécution des outils. |
| **Pas de vraie file d'approbation** | Les actions bloquées retournent un message demandant une confirmation manuelle de l'utilisateur, mais il n'y a pas de mécanisme cryptographique (ou hors-bande via Telegram) bloquant l'action côté serveur en attendant le clic. |
