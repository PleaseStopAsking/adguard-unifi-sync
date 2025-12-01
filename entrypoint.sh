#!/usr/bin/env sh
set -eu

# defaults
: "${CRON:=}"
: "${RUN_ON_START:=false}"

APP_CMD="python -u /app/unifi_adguard_client_sync.py"

# optional shell tracing
: "${ENTRYPOINT_TRACE:=false}"
case "${ENTRYPOINT_TRACE}" in
  true|"true"|1)
    set -x
    ;;
esac

log() {
  echo "[entrypoint] $1"
}

# if RUN_ON_START=true, run one sync immediately
case "${RUN_ON_START}" in
  true|"true"|1)
    log "Running initial sync..."
    if ! sh -lc "python -u /app/unifi_adguard_client_sync.py"; then
      log "Initial sync failed"
    fi
    ;;
  *)
    log "Skipping initial sync (RUN_ON_START=${RUN_ON_START})"
    ;;
esac

# if cron schedule provided, configure crond to run the app on that schedule
if [ -n "${CRON}" ]; then
  log "Configuring system crontab: ${CRON}"
  CRON_FILE="/etc/cron.d/adguard_unifi_sync"
  # trim any stray quotes from CRON value (POSIX-safe)
  CRON_CLEAN=$(printf "%s" "$CRON" | tr -d '"' | tr -d "'")
  cat > "${CRON_FILE}" <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
UNIFI_URL=${UNIFI_URL:-}
UNIFI_USERNAME=${UNIFI_USERNAME:-}
UNIFI_PW=${UNIFI_PW:-}
ADGUARD_URL=${ADGUARD_URL:-}
ADGUARD_USERNAME=${ADGUARD_USERNAME:-}
ADGUARD_PW=${ADGUARD_PW:-}
IGNORED_NETWORKS=${IGNORED_NETWORKS:-}
PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-1}
PYTHONDONTWRITEBYTECODE=${PYTHONDONTWRITEBYTECODE:-1}

${CRON_CLEAN} root sh -lc "${APP_CMD}" >> /proc/1/fd/1 2>> /proc/1/fd/2

EOF
  chmod 0644 "${CRON_FILE}" || true
  log "Starting cron in foreground..."
  exec cron -f
else
  log "No CRON provided; running app once and exiting"
  exec sh -lc "${APP_CMD}"
fi