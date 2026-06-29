#!/usr/bin/env bash
# Snapshot live SMSEagle APIv2 GET responses into mock/api/v2/<path>.json
# so the mock server can replay them offline.
#
# Usage:  ./tools/snapshot-api.sh
# Reads SMSEAGLE_API_URL + SMSEAGLE_ACCESS_TOKEN from .env (must point at LIVE device).
set -euo pipefail

cd "$(dirname "$0")/.."
set -a; source .env; set +a

BASE="${SMSEAGLE_API_URL%/}"
TOKEN="$SMSEAGLE_ACCESS_TOKEN"
OUT="mock/api/v2"

# Read-only endpoints worth capturing. Modem endpoints are expanded for modems 1 & 2.
endpoints=(
  "modem/full_info"
  "messages/count"
  "messages/whatsapp/count"
  "messages/signal/count"
  "messages/email/count"
  "users/count"
  "device/version"
  "device/support"
  "device/ha_failover/status"
  "device/email2sms/status"
  "device/email2sms_poller/status"
  "device/snmp/status"
  "device/data_conn/status"
  "device/smpp/status"
  "device/mqtt/status"
  "device/digital_io/external"
  "device/temperature_sensor/1/status"
  "device/temperature_sensor/1/read"
)
# Per-modem endpoints (modem_no in 1 2)
modem_paths=(
  "modem/full_info"
  "modem/signal"
  "modem/status"
  "modem/net_name"
  "modem/sim_status"
  "modem/network_registration_status"
  "modem/imei"
  "modem/imsi"
  "modem/number"
)
for p in "${modem_paths[@]}"; do
  for n in 1 2; do endpoints+=("$p/$n"); done
done

ok=0; skip=0
for ep in "${endpoints[@]}"; do
  url="$BASE/$ep?access_token=$TOKEN"
  [[ "$ep" == *temperature_sensor/*/read ]] && url="$url&scale=celsius"
  body="$(curl -sk -m 10 -w $'\n%{http_code}' "$url")"
  code="${body##*$'\n'}"
  json="${body%$'\n'*}"
  if [ "$code" = "200" ] && [ -n "$json" ]; then
    dest="$OUT/$ep.json"
    mkdir -p "$(dirname "$dest")"
    printf '%s' "$json" > "$dest"
    echo "  ok   $ep"
    ok=$((ok+1))
  else
    echo "  skip $ep (HTTP $code)"
    skip=$((skip+1))
  fi
done
echo "Captured $ok endpoint(s), skipped $skip. Files under $OUT/"
