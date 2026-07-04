#!/bin/bash
# AIDP Database Backup Script

BACKUP_DIR="/home/docker/AI-Code/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/aidp_backup_${TIMESTAMP}.sql.gz"

echo "[$TIMESTAMP] Starting AIDP database backup..."

docker exec novel-postgres pg_dump -U novel_os novel_os | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] Backup successful: $BACKUP_FILE"
    echo "[$TIMESTAMP] Size: $(du -h "$BACKUP_FILE" | cut -f1)"
    
    # Keep only last 7 backups
    ls -t "$BACKUP_DIR"/aidp_backup_*.sql.gz | tail -n +8 | xargs -r rm
    echo "[$TIMESTAMP] Old backups cleaned"
else
    echo "[$TIMESTAMP] Backup FAILED!"
fi
