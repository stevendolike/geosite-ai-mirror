#!/bin/sh
# Weekly refresh of /usr/share/xray/geosite-ai.dat from the mirror repo.
# Fetch -> sanity -> sha compare -> xray config test -> swap + restart, else rollback.
# Installed by Hermes; cron: 23 4 * * 1

URL_PRIMARY="https://cdn.jsdelivr.net/gh/stevendolike/geosite-ai-mirror@main/docs/geosite-ai.dat"
URL_FALLBACK="https://stevendolike.github.io/geosite-ai-mirror/geosite-ai.dat"
DAT="${DAT:-/usr/share/xray/geosite-ai.dat}"
BAK="${BAK:-/root/geosite-ai.dat.bak-auto}"
TMP="${TMP:-/tmp/geosite-ai-new.dat}"
CFG="/etc/xray/config.json"
ts() { date '+%Y-%m-%d %H:%M:%S'; }

rm -f "$TMP"
if ! uclient-fetch -qO "$TMP" -T 25 "$URL_PRIMARY" 2>/dev/null; then
  echo "$(ts) primary fetch failed, trying fallback"
  if ! uclient-fetch -qO "$TMP" -T 25 "$URL_FALLBACK" 2>/dev/null; then
    echo "$(ts) ERROR both fetch sources failed"; rm -f "$TMP"; exit 1
  fi
fi

sz=$(wc -c < "$TMP" 2>/dev/null || echo 0)
if [ "$sz" -lt 2000 ]; then
  echo "$(ts) ERROR payload too small ($sz bytes)"; rm -f "$TMP"; exit 1
fi
if ! grep -aq "CATEGORY-AI-!CN" "$TMP" || ! grep -aq "chatgpt.com" "$TMP"; then
  echo "$(ts) ERROR payload fails content gate (no category marker / chatgpt.com)"; rm -f "$TMP"; exit 1
fi

new=$(sha256sum "$TMP" | cut -d' ' -f1)
cur=$(sha256sum "$DAT" | cut -d' ' -f1)
if [ "$new" = "$cur" ]; then
  echo "$(ts) up to date ($new)"; rm -f "$TMP"; exit 0
fi

cp "$DAT" "$BAK"
mv "$TMP" "$DAT"
if XRAY_LOCATION_ASSET=/usr/share/xray xray run -test -c "$CFG" >/tmp/geosite-ai-test.log 2>&1; then
  [ "${NO_RESTART:-0}" = "1" ] || /etc/init.d/xray restart >/dev/null 2>&1
  sleep 2
  if netstat -ltn 2>/dev/null | grep -q ':12345'; then
    echo "$(ts) updated sha=$new, xray restarted OK"
  else
    echo "$(ts) WARN updated but xray port 12345 missing — rolling back"
    mv "$BAK" "$DAT"; [ "${NO_RESTART:-0}" = "1" ] || /etc/init.d/xray restart >/dev/null 2>&1
    exit 1
  fi
else
  echo "$(ts) ERROR new dat fails xray -test — rolled back, xray untouched"
  tail -3 /tmp/geosite-ai-test.log
  mv "$BAK" "$DAT"
  exit 1
fi
