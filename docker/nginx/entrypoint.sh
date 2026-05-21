#!/bin/sh
set -e

NGINX_MODE="${NGINX_MODE:-prod}"
DOMAIN="${CERTBOT_DOMAIN:-localhost}"

# ── Select the correct nginx config based on mode ─────────────────
if [ "$NGINX_MODE" = "dev" ]; then
    echo "==> Nginx mode: DEV (plain HTTP, no SSL)"
    cp /etc/nginx/conf.d/nginx-dev.conf /etc/nginx/conf.d/default.conf
else
    echo "==> Nginx mode: PROD (HTTPS with Let's Encrypt)"
    cp /etc/nginx/conf.d/nginx-prod.conf /etc/nginx/conf.d/default.conf

    # Substitute the domain placeholder in the prod config
    sed -i "s/\${CERTBOT_DOMAIN}/$DOMAIN/g" /etc/nginx/conf.d/default.conf

    # If certificates don't exist yet, use a self-signed placeholder so nginx can start.
    # Certbot will replace these once it runs successfully.
    CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
    if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
        echo "==> No TLS certificate found for $DOMAIN — generating temporary self-signed cert..."
        mkdir -p "$CERT_DIR"
        openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
            -keyout "$CERT_DIR/privkey.pem" \
            -out "$CERT_DIR/fullchain.pem" \
            -subj "/CN=$DOMAIN" 2>/dev/null
        echo "==> Temporary self-signed cert created. Run certbot to obtain a real certificate."
    fi
fi

# Generate htpasswd for monitoring endpoints (Prometheus, Loki)
# Uses MONITORING_USER / MONITORING_PASSWORD env vars (defaults: admin/admin)
HTPASSWD_FILE="/etc/nginx/.htpasswd"
MONITORING_USER="${MONITORING_USER:-admin}"
MONITORING_PASSWORD="${MONITORING_PASSWORD:-admin}"
htpasswd -cb "$HTPASSWD_FILE" "$MONITORING_USER" "$MONITORING_PASSWORD" 2>/dev/null
echo "==> htpasswd generated for monitoring endpoints (user: $MONITORING_USER)"

if [ "${NGINX_AUTO_RELOAD_ENABLE:-0}" = "1" ]; then
    /usr/local/bin/nginx_auto_reload.sh &
fi

exec "$@"
