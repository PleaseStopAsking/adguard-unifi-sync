# AdGuard ⇄ Unifi Client Sync

Synchronize active client information from a Unifi OS controller into AdGuard Home's client list. Each run:
- Authenticates to Unifi and AdGuard
- Retrieves currently active Unifi clients (optionally ignoring specified network names)
- Adds new clients to AdGuard or updates existing client IP / name entries based on MAC address
- Emits a summary of changes

## Why
AdGuard Home benefits from accurate per-device naming and IP mappings for query logs, filtering rules, and per-client overrides. Unifi already knows device names, MACs, and stable IPs. This tool keeps AdGuard aligned with Unifi so you avoid manual editing or stale host/IP data.

## Key Features
- Uses MAC address as stable identifier across both systems
- Optional ignore list for specific Unifi network names (e.g. Guest, IoT)
- Safe updates: only adds/updates clients when differences detected
- Flexible runtime: run once and exit, run on a CRON schedule, or run once at startup before scheduling
- Environment-variable or CLI flag configuration for credentials and URLs
- Graceful logging

## Runtime Modes
There are two primary execution modes controlled by environment variables:
1. Single Run (default when `CRON` unset): container starts and does a single run of the script, then exits.
2. Scheduled Run (when `CRON` is set): starts `cron -f` and executes the sync script per the provided CRON expression. Optionally performs one immediate run first if `RUN_ON_START=true`.

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `UNIFI_URL` | Yes | Base URL of Unifi OS (e.g. `https://controller.local`) |
| `UNIFI_USERNAME` | Yes | Unifi username |
| `UNIFI_PW` | Yes | Unifi password (or use `--unifi-password`) |
| `ADGUARD_URL` | Yes | Base URL of AdGuard Home (e.g. `http://adguard:3000`) |
| `ADGUARD_USERNAME` | Yes | AdGuard username |
| `ADGUARD_PW` | Yes | AdGuard password (or use `--adguard-password`) |
| `IGNORED_NETWORKS` | No | Comma-delimited list of Unifi network names to skip (e.g. `Guest,IoT`) |
| `CRON` | No | CRON expression for scheduled runs (e.g. `*/15 * * * *`) |
| `RUN_ON_START` | No | `true` to force an immediate sync before scheduling |
| `ENTRYPOINT_TRACE` | No | `true` to enable shell `set -x` tracing for entrypoint debugging |

## CLI Flags (Alternative to Env Vars when running script directly)
```
python unifi_adguard_client_sync.py \
  --unifi-url https://controller.example \
  --unifi-username admin \
  --unifi-password secret \
  --adguard-url http://adguard:3000 \
  --adguard-username admin \
  --adguard-password secret \
  --ignored-networks "Guest,IoT"
```

## Docker Build & Run
### Build Locally
```bash
docker build -t adguard-unifi-sync:latest .
```

### One-Off Run (Single Execution)
Runs once then exits:
```bash
docker run --rm \
  -e UNIFI_URL=https://10.0.0.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PW=changeme \
  -e ADGUARD_URL=http://10.0.0.48 \
  -e ADGUARD_USERNAME=admin \
  -e ADGUARD_PW=changeme \
  adguard-unifi-sync:latest
```

### Scheduled via CRON (Every 15 Minutes)
```bash
docker run --rm \
  -e UNIFI_URL=https://10.0.0.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PW=changeme \
  -e ADGUARD_URL=http://10.0.0.48 \
  -e ADGUARD_USERNAME=admin \
  -e ADGUARD_PW=changeme \
  -e CRON="*/15 * * * *" \
  -e RUN_ON_START=true \
  adguard-unifi-sync:latest
```

### Enable Shell Trace (Debugging EntryPoint)
```bash
docker run --rm -e ENTRYPOINT_TRACE=true ... adguard-unifi-sync:latest
```

## Docker Compose Example
The provided `compose.yml` can be adapted—example below sanitizes secrets:
```yaml
services:
  adguard-unifi-sync:
    build:
      context: .
    container_name: adguard-unifi-sync
    restart: always
    environment:
      UNIFI_URL: https://10.0.0.1
      UNIFI_USERNAME: admin
      UNIFI_PW: changeme
      ADGUARD_URL: http://10.0.0.48
      ADGUARD_USERNAME: admin
      ADGUARD_PW: changeme
      IGNORED_NETWORKS: Guest,Untrusted
      CRON: "*/5 * * * *"   # every 5 minutes
      RUN_ON_START: "true"
```
Run with:
```bash
docker compose up -d --build
```

Optional: Put secrets in a `.env` file alongside `compose.yml`:
```
UNIFI_PW=super-secret-unifi
ADGUARD_PW=super-secret-adguard
```

## Security Notes
- Use strong passwords and avoid committing them into version control (prefer `.env`).
- HTTPS verification is currently disabled for Unifi (`verify=False`); consider enabling certificate validation in production environments.
- Least privilege for the Unifi and AdGuard accounts is recommended.

## Contributing
1. Fork / branch
2. Make changes
3. Update README or comments if behavior changes
4. Open PR (include rationale and testing notes)

## License
MIT

---
Suggestions or feature requests welcome.
