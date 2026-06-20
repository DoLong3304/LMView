#!/usr/bin/env sh
set -eu

TOKEN="${DUCKDNS_TOKEN:-}"
SUBDOMAINS="${DUCKDNS_SUBDOMAINS:-}"
INTERVAL="${DUCKDNS_UPDATE_INTERVAL_SECONDS:-300}"

if [ -z "$TOKEN" ] || [ -z "$SUBDOMAINS" ] || [ "$TOKEN" = "change-me" ] || [ "$SUBDOMAINS" = "your-subdomain" ]; then
  echo "[duckdns-auto] DUCKDNS_TOKEN or DUCKDNS_SUBDOMAINS is not set; sleeping."
  exec sleep infinity
fi

echo "[duckdns-auto] Starting dynamic DNS updates for: $SUBDOMAINS"
while true; do
  IFS=','
  for subdomain in $SUBDOMAINS; do
    # IB-5: Token in URL could leak in curl error output. Capture stderr separately
    # and strip token before logging. Use temp file for stderr capture.
    errfile=$(mktemp /tmp/duckdns-err-XXXXXX)
    response=$(curl -fsS "https://www.duckdns.org/update?domains=${subdomain}&token=${TOKEN}&ip=" 2>"$errfile" || true)
    if [ -s "$errfile" ]; then
      # Log masked version of the error (strip token from URL in error output)
      masked_err=$(sed 's/token=[^&[:space:]]*/token=****/g' "$errfile")
      echo "[duckdns-auto] Error for ${subdomain}.duckdns.org: ${masked_err}"
    fi
    rm -f "$errfile"
    if [ "$response" = "OK" ]; then
      echo "[duckdns-auto] Updated ${subdomain}.duckdns.org"
    else
      echo "[duckdns-auto] Update failed for ${subdomain}.duckdns.org (response: ${response})"
    fi
  done
  unset IFS

  sleep "$INTERVAL"
done
