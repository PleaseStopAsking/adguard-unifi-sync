FROM python:3.11-slim

LABEL org.opencontainers.image.title="adguard-unifi-sync" \
      org.opencontainers.image.description="Sync active Unifi clients into AdGuard Home client list" \
      org.opencontainers.image.source="https://github.com/PleaseStopAsking/adguard-unifi-sync" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# install dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
      && apt-get update \
      && apt-get install -y --no-install-recommends cron \
      && rm -rf /var/lib/apt/lists/*

# copy script
COPY unifi_adguard_client_sync.py ./

# lightweight timed entrypoint
COPY entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]