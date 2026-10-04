#!/usr/bin/env bash
#
# Jarvis CLI Ops Terminal
# Script d'exploitation et de gestion pour Jarvis (Proxmox VE / LXC 100)

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR" || exit 1

# Couleurs ANSI
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}${BOLD}========================================${NC}"
    echo -e "${CYAN}${BOLD}       🤖 JARVIS CLI OPS TERMINAL       ${NC}"
    echo -e "${CYAN}${BOLD}========================================${NC}"
}

usage() {
    print_header
    echo -e "${BOLD}Usage:${NC} $0 {deploy|logs|status}"
    echo ""
    echo -e "  ${GREEN}deploy${NC}  🚀 Exécute le pipeline complet de déploiement vers LXC 100"
    echo -e "  ${BLUE}logs${NC}    📋 Affiche et suit les logs Docker de Jarvis en direct"
    echo -e "  ${YELLOW}status${NC}  📊 Affiche l'état des conteneurs Docker sur LXC 100"
    echo ""
    exit 1
}

case "$1" in
    deploy)
        print_header
        echo -e "${YELLOW}📦 [1/4] Création de l'archive de mise à jour...${NC}"
        tar -czf jarvis_update.tar.gz -C "$BASE_DIR" src/jarvis data tests pyproject.toml pytest.ini db scripts requirements.txt Dockerfile .env.example docker-compose.yml Caddyfile

        echo -e "${BLUE}🚀 [2/4] Copie de l'archive vers Proxmox VE (pve)...${NC}"
        scp jarvis_update.tar.gz pve:/tmp/

        echo -e "${CYAN}🐳 [3/4] Déploiement dans LXC 100, reconstruction et relance du conteneur...${NC}"
        ssh pve 'pct push 100 /tmp/jarvis_update.tar.gz /tmp/jarvis_update.tar.gz && pct exec 100 -- bash -c "tar -xzf /tmp/jarvis_update.tar.gz -C /app && rm /tmp/jarvis_update.tar.gz && chown -R 1001:1001 /app && cd /app && docker compose up -d --build"'

        echo -e "${YELLOW}🧹 [4/4] Suppression de l'archive locale...${NC}"
        rm -f jarvis_update.tar.gz

        echo -e "${GREEN}${BOLD}✨ Déploiement de Jarvis terminé avec succès !${NC}"
        ;;

    logs)
        print_header
        echo -e "${BLUE}📋 Connexion aux logs du conteneur Jarvis (Ctrl+C pour quitter)...${NC}"
        ssh pve "pct exec 100 -- docker logs -f jarvis"
        ;;

    status)
        print_header
        echo -e "${YELLOW}📊 Statut des conteneurs Docker sur LXC 100 :${NC}"
        ssh pve "pct exec 100 -- docker ps"
        ;;

    *)
        usage
        ;;
esac
