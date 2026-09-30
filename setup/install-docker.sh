#!/usr/bin/env bash
set -euo pipefail

# Couleurs pour les messages de sortie
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Installation de Docker et Tailscale ===${NC}"

# Mise à jour des paquets
echo -e "${YELLOW}Mise à jour du système...${NC}"
apt-get update
apt-get upgrade -y

# Installation des dépendances pour Docker
echo -e "${YELLOW}Installation des dépendances...${NC}"
apt-get install -y ca-certificates curl gnupg lsb-release

# Ajout de la clé GPG officielle de Docker
echo -e "${YELLOW}Configuration du dépôt Docker officiel...${NC}"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Ajout du dépôt Docker aux sources APT
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installation de Docker Engine et du plugin Compose
echo -e "${YELLOW}Installation de Docker Engine et Docker Compose...${NC}"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Activation et démarrage du service Docker
echo -e "${YELLOW}Activation du service Docker...${NC}"
systemctl enable docker
systemctl start docker

# Ajout de l'utilisateur courant au groupe docker
# (Si exécuté en root, on l'ajoute potentiellement pour un autre utilisateur comme 'ubuntu')
USER_TO_ADD=${SUDO_USER:-root}
if id "ubuntu" &>/dev/null; then
    USER_TO_ADD="ubuntu"
fi

if [ "$USER_TO_ADD" != "root" ]; then
    echo -e "${YELLOW}Ajout de l'utilisateur $USER_TO_ADD au groupe docker...${NC}"
    usermod -aG docker "$USER_TO_ADD"
fi

# Installation de Tailscale
echo -e "${YELLOW}Installation de Tailscale...${NC}"
curl -fsSL https://tailscale.com/install.sh | sh

# Vérification finale
echo -e "${YELLOW}Vérification de l'installation de Docker avec 'hello-world'...${NC}"
docker run --rm hello-world

echo -e "${GREEN}Installation terminée avec succès !${NC}"
echo -e "${YELLOW}Note : Si vous avez ajouté un utilisateur au groupe docker, il devra se reconnecter pour que les changements prennent effet.${NC}"
echo -e "${YELLOW}Pour configurer Tailscale, exécutez : sudo tailscale up${NC}"
