#!/usr/bin/env bash
# Bootstrap HTTPS automation variables and start automation services.
# Usage: ./init_certbot.sh <domain> <email>
#
# The domain can be any publicly reachable domain:
#   - DuckDNS:  myapp.duckdns.org
#   - Custom:   trading.example.com
#
# If the domain is a *.duckdns.org host AND DUCKDNS_SUBDOMAINS is not already
# set in .env, the script will auto-populate it. Otherwise DuckDNS settings
# are left untouched (you can add them manually if needed).
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> <email>}"
EMAIL="${2:?Usage: $0 <domain> <email>}"
ENV_FILE=".env"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  touch "$ENV_FILE"
fi

upsert_env() {
  key="$1"
  value="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    printf "%s=%s\n" "$key" "$value" >> "$ENV_FILE"
  fi
}

upsert_env "CERTBOT_DOMAIN" "$DOMAIN"
upsert_env "CERTBOT_EMAIL" "$EMAIL"

# If the domain is a duckdns host, auto-populate DUCKDNS_SUBDOMAINS if not set.
if [[ "$DOMAIN" =~ ^([a-zA-Z0-9-]+)\.duckdns\.org$ ]]; then
  DUCK_SUBDOMAIN="${BASH_REMATCH[1]}"
  if ! grep -q '^DUCKDNS_SUBDOMAINS=' "$ENV_FILE"; then
    upsert_env "DUCKDNS_SUBDOMAINS" "$DUCK_SUBDOMAIN"
  fi
fi

# Ensure automation toggles have sane defaults.
if ! grep -q '^CERTBOT_RENEW_INTERVAL_SECONDS=' "$ENV_FILE"; then
  upsert_env "CERTBOT_RENEW_INTERVAL_SECONDS" "43200"
fi
if ! grep -q '^NGINX_AUTO_RELOAD_ENABLE=' "$ENV_FILE"; then
  upsert_env "NGINX_AUTO_RELOAD_ENABLE" "1"
fi
if ! grep -q '^NGINX_RELOAD_INTERVAL_SECONDS=' "$ENV_FILE"; then
  upsert_env "NGINX_RELOAD_INTERVAL_SECONDS" "21600"
fi
if ! grep -q '^DUCKDNS_UPDATE_INTERVAL_SECONDS=' "$ENV_FILE"; then
  upsert_env "DUCKDNS_UPDATE_INTERVAL_SECONDS" "300"
fi

echo "Starting HTTPS automation services..."
SERVICES="nginx-prod certbot-auto"

# Only start duckdns-auto if DuckDNS is configured
if grep -q '^DUCKDNS_TOKEN=' "$ENV_FILE" && ! grep -q '^DUCKDNS_TOKEN=change-me' "$ENV_FILE"; then
  SERVICES="$SERVICES duckdns-auto"
fi

docker compose --profile prod up -d $SERVICES

echo ""
echo "Current service status:"
docker compose ps nginx-prod certbot-auto 2>/dev/null || true

echo ""
echo "Recent certbot logs:"
docker logs --tail 20 certbot-auto 2>/dev/null || true

# Show duckdns logs only if the service is running
if docker ps --format '{{.Names}}' | grep -q duckdns-auto; then
  echo ""
  echo "Recent duckdns logs:"
  docker logs --tail 20 duckdns-auto 2>/dev/null || true
fi

echo ""
echo "Bootstrap complete for https://${DOMAIN}"
