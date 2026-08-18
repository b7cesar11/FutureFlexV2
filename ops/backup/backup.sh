#!/usr/bin/env bash
set -Eeuo pipefail

required_vars=(
  BACKUP_MONGO_URL
  BACKUP_DB_NAME
  BACKUP_BUCKET
  BACKUP_S3_ENDPOINT
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  BACKUP_ENCRYPTION_PASSPHRASE
)

for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 2
  fi
done

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"
BACKUP_PREFIX="${BACKUP_PREFIX:-futureflex}"
BACKUP_TIMEZONE="${BACKUP_TIMEZONE:-America/Sao_Paulo}"
BACKUP_RETENTION_DAILY="${BACKUP_RETENTION_DAILY:-14}"
BACKUP_RETENTION_WEEKLY="${BACKUP_RETENTION_WEEKLY:-8}"
BACKUP_RETENTION_MONTHLY="${BACKUP_RETENTION_MONTHLY:-12}"

aws configure set default.s3.addressing_style path >/dev/null

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
local_day="$(TZ="$BACKUP_TIMEZONE" date +%F)"
weekday="$(TZ="$BACKUP_TIMEZONE" date +%u)"
day_of_month="$(TZ="$BACKUP_TIMEZONE" date +%d)"
safe_db="$(printf '%s' "$BACKUP_DB_NAME" | tr -cd '[:alnum:]_.-')"
archive="$workdir/${safe_db}_${stamp}.archive.gz"
encrypted="$archive.enc"

printf 'Creating MongoDB dump for %s at %s...\n' "$BACKUP_DB_NAME" "$stamp"
mongodump \
  --uri="$BACKUP_MONGO_URL" \
  --db="$BACKUP_DB_NAME" \
  --archive="$archive" \
  --gzip

if [[ ! -s "$archive" ]]; then
  echo "Backup archive is empty; refusing to upload." >&2
  exit 3
fi

printf 'Encrypting backup before upload...\n'
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
  -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
  -in "$archive" \
  -out "$encrypted"

if [[ ! -s "$encrypted" ]]; then
  echo "Encrypted backup is empty; refusing to upload." >&2
  exit 4
fi

sha256="$(sha256sum "$encrypted" | awk '{print $1}')"
size="$(stat -c %s "$encrypted")"
filename="$(basename "$encrypted")"

upload_object() {
  local tier="$1"
  local key="${BACKUP_PREFIX}/${tier}/${local_day}/${filename}"

  aws s3api put-object \
    --endpoint-url "$BACKUP_S3_ENDPOINT" \
    --bucket "$BACKUP_BUCKET" \
    --key "$key" \
    --body "$encrypted" \
    --metadata "sha256=${sha256},db=${safe_db},created_utc=${stamp}" \
    --content-type application/octet-stream \
    >/dev/null

  remote_size="$(aws s3api head-object \
    --endpoint-url "$BACKUP_S3_ENDPOINT" \
    --bucket "$BACKUP_BUCKET" \
    --key "$key" \
    --query ContentLength \
    --output text)"

  if [[ "$remote_size" != "$size" ]]; then
    echo "Remote backup size mismatch for ${key}: local=${size}, remote=${remote_size}" >&2
    exit 5
  fi

  printf 'Uploaded %s (%s bytes, sha256=%s)\n' "$key" "$size" "$sha256"
}

prune_tier() {
  local tier="$1"
  local keep="$2"
  local prefix="${BACKUP_PREFIX}/${tier}/"

  if ! [[ "$keep" =~ ^[0-9]+$ ]]; then
    echo "Invalid retention count for ${tier}: ${keep}" >&2
    exit 6
  fi

  mapfile -t keys < <(
    aws s3api list-objects-v2 \
      --endpoint-url "$BACKUP_S3_ENDPOINT" \
      --bucket "$BACKUP_BUCKET" \
      --prefix "$prefix" \
      --query 'reverse(sort_by(Contents,&LastModified))[].Key' \
      --output text \
      | tr '\t' '\n' \
      | grep -v '^None$' \
      | sed '/^$/d'
  )

  if (( ${#keys[@]} <= keep )); then
    return
  fi

  for ((i=keep; i<${#keys[@]}; i++)); do
    aws s3api delete-object \
      --endpoint-url "$BACKUP_S3_ENDPOINT" \
      --bucket "$BACKUP_BUCKET" \
      --key "${keys[$i]}" \
      >/dev/null
    printf 'Pruned old %s backup: %s\n' "$tier" "${keys[$i]}"
  done
}

upload_object daily

# Sunday snapshot for medium-term recovery.
if [[ "$weekday" == "7" ]]; then
  upload_object weekly
fi

# First day of each month for long-term recovery.
if [[ "$day_of_month" == "01" ]]; then
  upload_object monthly
fi

prune_tier daily "$BACKUP_RETENTION_DAILY"
prune_tier weekly "$BACKUP_RETENTION_WEEKLY"
prune_tier monthly "$BACKUP_RETENTION_MONTHLY"

echo "Future Flex backup completed successfully."
