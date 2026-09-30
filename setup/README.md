# Configuration de l'infrastructure Jarvis

Ce répertoire contient les scripts nécessaires pour configurer l'environnement d'hébergement du projet Jarvis sur un serveur Proxmox.

## Prérequis

- Un serveur Proxmox VE fonctionnel avec un accès shell (SSH ou console web).
- Un stockage nommé `local-lvm` configuré sur Proxmox.
- Une connexion Internet pour télécharger le template Ubuntu, Docker et Tailscale.

## Étape 1 : Créer le conteneur LXC sur Proxmox

Ce script doit être exécuté **sur l'hôte Proxmox**. Il va créer un conteneur LXC (ID: 100) avec Ubuntu 24.04, 12 Go de RAM, 4 cœurs et 200 Go d'espace disque.

1. Transférez le script `create-lxc.sh` sur votre hôte Proxmox.
2. Rendez le script exécutable :
   ```bash
   chmod +x create-lxc.sh
   ```
3. Exécutez le script :
   ```bash
   ./create-lxc.sh
   ```

*Note : Le script est idempotent. Si le conteneur 100 existe déjà, il ne sera pas recréé.*

## Étape 2 : Installer Docker et Tailscale dans le conteneur

Une fois le conteneur démarré, vous devez vous y connecter et exécuter le script d'installation.

1. Connectez-vous au conteneur depuis Proxmox :
   ```bash
   pct enter 100
   ```
2. Transférez ou copiez le contenu du script `install-docker.sh` dans le conteneur.
3. Rendez-le exécutable :
   ```bash
   chmod +x install-docker.sh
   ```
4. Lancez l'installation :
   ```bash
   ./install-docker.sh
   ```

Ce script va installer Docker Engine (dépôt officiel), le plugin Docker Compose, et Tailscale pour l'accès distant. Il validera l'installation avec `docker run hello-world`.

## Étape 3 : Lancer le projet Jarvis

Après avoir configuré Docker et Tailscale :

1. Clonez le dépôt du projet Jarvis dans le conteneur (dans `/opt` ou `/home/ubuntu`).
2. Assurez-vous d'être dans le bon répertoire.
3. Lancez les services avec Docker Compose :
   ```bash
   docker compose up -d
   ```

## Dépannage

- **Problèmes de permissions Docker / Conteneurs bloqués :** 
  Par défaut, LXC applique des profils de sécurité qui peuvent bloquer certaines fonctionnalités de Docker (comme la création d'interfaces réseau ou le montage de volumes).
  Si vos conteneurs Docker refusent de démarrer ou affichent des erreurs de permissions, modifiez la configuration LXC sur l'hôte Proxmox :
  1. Ouvrez le fichier de configuration : `nano /etc/pve/lxc/100.conf`
  2. Ajoutez la ligne suivante à la fin du fichier : `lxc.apparmor.profile: unconfined`
  3. Redémarrez le conteneur LXC : `pct stop 100 && pct start 100`

- **Accès à Tailscale :**
  N'oubliez pas d'exécuter `sudo tailscale up` dans le conteneur et de suivre le lien fourni pour authentifier la machine sur votre réseau Tailscale.
