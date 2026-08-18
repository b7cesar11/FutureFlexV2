FROM mongo:7

RUN apt-get update \
    && apt-get install -y --no-install-recommends awscli ca-certificates openssl \
    && rm -rf /var/lib/apt/lists/*

COPY ops/backup/backup.sh /usr/local/bin/futureflex-backup
COPY ops/backup/restore.sh /usr/local/bin/futureflex-restore

RUN chmod +x /usr/local/bin/futureflex-backup /usr/local/bin/futureflex-restore

ENTRYPOINT ["/usr/local/bin/futureflex-backup"]
