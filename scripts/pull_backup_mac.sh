#!/bin/bash
set -euo pipefail

PROXMOX_IP="192.168.2.76" # IP Locale ou Tailscale
LXC_USER="root"
REMOTE_DIR="/opt/jarvis/backups/db"
LOCAL_DIR="$HOME/JarvisBackups"

mkdir -p "$LOCAL_DIR"
rsync -avz --delete -e "ssh" "${LXC_USER}@${PROXMOX_IP}:${REMOTE_DIR}/" "$LOCAL_DIR/"
echo "✅ Synchronisation depuis le LXC terminée."
