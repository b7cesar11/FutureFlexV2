#!/usr/bin/env bash
set -Eeuo pipefail

required_vars=(
  BACKUP_BUCKET
  BACKUP_S3_ENDPOINT
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  BACKUP_ENCRYPTION_PASSPHRASE
  BACKUP_OBJECT_KEY
  BACKUP_DB_NAME
  RESTORE_MONGO_URL
  RESTORE_DB_NAME
)

for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 2
  fi
done

if [[ "$RESTORE_DB_NAME" == "$BACKUP_DB_NAME" && "${ALLOW_PRODUCTION_RESTORE:-false}" != "true" ]]; then
  echo "Refusing to restore over the source database. Set ALLOW_PRODUCTION_RESTORE=true only for an intentional disaster recovery operation." >&2
  exit 3
fi

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"
aws configure set default.s3.addressing_style path >/dev/null

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

encrypted="$workdir/backup.enc"
archive="$workdir/backup.archive.gz"

printf 'Downloading %s...\n' "$BACKUP_OBJECT_KEY"
aws s3api get-object \
  --endpoint-url "$BACKUP_S3_ENDPOINT" \
  --bucket "$BACKUP_BUCKET" \
  --key "$BACKUP_OBJECT_KEY" \
  "$encrypted" \
  >/dev/null

expected_sha="$(aws s3api head-object \
  --endpoint-url "$BACKUP_S3_ENDPOINT" \
  --bucket "$BACKUP_BUCKET" \
  --key "$BACKUP_OBJECT_KEY" \
  --query 'Metadata.sha256' \
  --output text)"
actual_sha="$(sha256sum "$encrypted" | awk '{print $1}')"

if [[ -z "$expected_sha" || "$expected_sha" == "None" || "$expected_sha" != "$actual_sha" ]]; then
  echo "Backup checksum validation failed." >&2
  exit 4
fi

printf 'Checksum OK. Decrypting backup...\n'
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
  -in "$encrypted" \
  -out "$archive"

if [[ ! -s "$archive" ]]; then
  echo "Decrypted archive is empty." >&2
  exit 5
fi

printf 'Restoring %s into %s...\n' "$BACKUP_DB_NAME" "$RESTORE_DB_NAME"
mongorestore \
  --uri="$RESTORE_MONGO_URL" \
  --archive="$archive" \
  --gzip \
  --drop \
  --nsInclude="${BACKUP_DB_NAME}.*" \
  --nsFrom="${BACKUP_DB_NAME}.*" \
  --nsTo="${RESTORE_DB_NAME}.*"

echo "Future Flex restore completed successfully."
