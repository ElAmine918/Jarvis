#!/bin/bash
set -euo pipefail
BACKUP_DIR="/opt/jarvis/backups/db"
docker compose exec -T pgvector pg_dump -U jarvis -d jarvis_memory -F c > ${BACKUP_DIR}/dump.tmp
mv ${BACKUP_DIR}/dump.tmp ${BACKUP_DIR}/dump.dump
find ${BACKUP_DIR} -mtime +7 -delete
