#!/usr/bin/env bash
# Deploy/update on the VPS. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/XolmatovBoburbek/davidzakirov/main/deploy.sh | bash
# Asks for the admin password on first run; re-run to pull updates.
set -euo pipefail
DIR=/root/davidzakirov
PORT=${PORT:-8010}   # ponytail: fixed port; put nginx/Caddy in front when a domain is ready

if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q https://github.com/XolmatovBoburbek/davidzakirov "$DIR"; fi
cd "$DIR"

if [ ! -f .env ]; then
  read -rsp "Admin password: " PW </dev/tty; echo
  printf 'ADMIN_PASSWORD=%s\nPORT=%s\nSITE_NAME=DAVID ZAKIROV\nSITE_TAGLINE=Director & Editor\n' "$PW" "$PORT" > .env
  chmod 600 .env
fi

set -a; . ./.env; set +a
pm2 delete davidzakirov >/dev/null 2>&1 || true
pm2 start app.py --name davidzakirov --interpreter python3 --update-env
pm2 save >/dev/null
echo "site:  http://$(curl -s -4 ifconfig.me || hostname -I | awk '{print $1}'):$PORT"
echo "admin: same URL + /admin"
