#!/usr/bin/env bash
set -euo pipefail
umask 077
backup_dir="${1:?Usage: backup.sh /chemin/sauvegardes}"
mkdir -p "$backup_dir"
backup_file="${backup_dir}/merifield-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_file"
test -s "$backup_file"
printf 'Sauvegarde PostgreSQL créée : %s\n' "$backup_file"
printf 'Copier aussi les médias, .env et les objets S3 vers une destination externe protégée.\n'
