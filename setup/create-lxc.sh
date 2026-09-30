#!/usr/bin/env bash
set -euo pipefail

# Couleurs pour les messages de sortie
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paramètres du conteneur
CT_ID=100
CT_NAME="docker-host"
STORAGE="local-lvm"
RAM=12288 # 12GB en MB
CORES=4
DISK="140G"
NETWORK="name=eth0,bridge=vmbr0,ip=dhcp"

echo -e "${GREEN}=== Création du conteneur LXC $CT_NAME (ID: $CT_ID) ===${NC}"

# Vérifier si le conteneur existe déjà
if pct status $CT_ID &>/dev/null; then
    echo -e "${YELLOW}Le conteneur $CT_ID existe déjà. Création ignorée.${NC}"
else
    # Téléchargement du template Ubuntu 24.04 (au cas où il n'est pas déjà présent)
    echo -e "${YELLOW}Mise à jour de la liste des templates...${NC}"
    pveam update
    
    echo -e "${YELLOW}Téléchargement du template Ubuntu 24.04...${NC}"
    # Note: On récupère le nom exact du template disponible
    TEMPLATE_NAME=$(pveam available -section system | grep ubuntu-24.04-standard | awk '{print $2}' | head -n 1)
    if [ -z "$TEMPLATE_NAME" ]; then
        echo -e "${RED}Impossible de trouver un template pour Ubuntu 24.04.${NC}"
        exit 1
    fi
    pveam download local $TEMPLATE_NAME || true
    
    TEMPLATE_PATH="local:vztmpl/$(basename $TEMPLATE_NAME)"

    # Création du conteneur
    echo -e "${YELLOW}Création du conteneur avec $CORES cœurs, $RAM MB de RAM, et $DISK de disque...${NC}"
    pct create $CT_ID $TEMPLATE_PATH \
        --arch amd64 \
        --hostname $CT_NAME \
        --cores $CORES \
        --memory $RAM \
        --swap 0 \
        --net0 $NETWORK \
        --rootfs $STORAGE:$DISK \
        --features nesting=1,keyctl=1 \
        --unprivileged 1

    echo -e "${GREEN}Conteneur créé avec succès.${NC}"
    
    # Configuration supplémentaire pour Docker (AppArmor)
    # Note : Si Docker a des problèmes de permissions, vous pouvez ajouter 'lxc.apparmor.profile: unconfined' 
    # dans le fichier de configuration (/etc/pve/lxc/$CT_ID.conf)
    echo -e "${YELLOW}Note : Si vous rencontrez des problèmes avec Docker, ajoutez 'lxc.apparmor.profile: unconfined' dans /etc/pve/lxc/$CT_ID.conf${NC}"
fi

# Démarrer le conteneur
echo -e "${YELLOW}Démarrage du conteneur...${NC}"
pct start $CT_ID

echo -e "${GREEN}Le conteneur $CT_NAME est démarré et prêt.${NC}"
