# Système de Compétences (Skills) - Jarvis

Ce répertoire est prévu pour contenir des exports ou des notes relatives aux compétences apprises par Jarvis, bien que la mémoire principale (skills et faits) soit stockée dans la base de données SQLite (`memory.db`).

## Comment ça marche ?

Jarvis dispose d'une mémoire persistante grâce au module `memory.py` qui utilise `aiosqlite`.

1. **Apprentissage Automatique** : Lorsque vous demandez à Jarvis de se souvenir d'une procédure ou d'une préférence, il peut utiliser l'outil (ou son prompt système l'y encourage) pour sauvegarder ces informations sous forme de "Skill" ou de "Fact" dans la base de données.
2. **Recherche** : Jarvis peut rechercher dans cette mémoire pour retrouver des commandes fréquentes ou des contextes spécifiques.
3. **Commandes Telegram** : Vous pouvez taper `/skills` dans Telegram pour lister toutes les compétences qu'il a mémorisées.

## Structure de la base

- **Table `skills`** : id, name, description, content (markdown), created_at, last_used_at, use_count
- **Table `facts`** : id, key, value, created_at

*Note : Les données sont stockées dans le chemin configuré par la variable d'environnement `MEMORY_DB_PATH` (par défaut `/app/data/memory.db`).*
