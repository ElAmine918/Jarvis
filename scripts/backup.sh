#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/jarvis/backups/db"
DB_USER="jarvis"
DB_NAME="jarvis_memory"
DATE=$(date +"%Y%m%d_%H%M%S")
TMP_FILE="${BACKUP_DIR}/jarvis_mem_${DATE}.tmp"
FINAL_FILE="${BACKUP_DIR}/jarvis_mem_${DATE}.dump"

mkdir -p "$BACKUP_DIR"
trap 'rm -f "$TMP_FILE"' ERR EXIT

echo "⏳ Dump SQL en cours..."
cd /opt/jarvis || cd /app || cd /Users/amine/Code/MyCloud
docker compose exec -T pgvector pg_dump -U "$DB_USER" -d "$DB_NAME" -F c > "$TMP_FILE"

mv "$TMP_FILE" "$FINAL_FILE"
trap - ERR EXIT 

echo "✅ Backup terminé : $FINAL_FILE"
find "$BACKUP_DIR" -type f -name "jarvis_mem_*.dump" -mtime +7 -delete
