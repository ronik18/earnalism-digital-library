#!/usr/bin/env sh
set -eu

PROJECT_DIR=${PROJECT_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
BACKUP_DIR=${BACKUP_DIR:-"$PROJECT_DIR/backups"}
STAMP=$(date -u +"%Y%m%dT%H%M%SZ")

mkdir -p "$BACKUP_DIR"
cd "$PROJECT_DIR"

docker compose --env-file deploy/production.env -f docker-compose.prod.yml exec -T mongo \
  mongodump --archive --gzip \
  > "$BACKUP_DIR/mongo-$STAMP.archive.gz"

find "$BACKUP_DIR" -name 'mongo-*.archive.gz' -type f -mtime +14 -delete

echo "Mongo backup written to $BACKUP_DIR/mongo-$STAMP.archive.gz"
