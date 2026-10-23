#!/usr/bin/env bash
# Deploy/update on the VPS. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/XolmatovBoburbek/davidzakirov/main/deploy.sh | bash
# Asks for the admin password on first run; re-run to pull updates.
# With a domain pointed at this server (nginx + certbot):
#   curl -fsSL .../deploy.sh | DOMAIN=portfolio.example.com bash
set -euo pipefail
DIR=/root/davidzakirov
PORT=${PORT:-8010}   # ponytail: fixed port; put nginx/Caddy in front when a domain is ready

if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q https://github.com/XolmatovBoburbek/davidzakirov "$DIR"; fi
cd "$DIR"

if [ ! -f .env ]; then
  read -rsp "Admin password: " PW </dev/tty; echo
  printf 'ADMIN_PASSWORD=%q\nPORT=%q\nSITE_NAME=%q\nSITE_TAGLINE=%q\n' "$PW" "$PORT" "DAVID ZAKIROV" "Director & Editor" > .env
  chmod 600 .env
fi

set -a; . ./.env; set +a
pm2 delete davidzakirov >/dev/null 2>&1 || true
pm2 start app.py --name davidzakirov --interpreter python3 --update-env
pm2 save >/dev/null
if [ -n "${DOMAIN:-}" ] && command -v nginx >/dev/null; then
  cat > /etc/nginx/sites-available/davidzakirov <<CONF
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 25m;
    location / { proxy_pass http://127.0.0.1:$PORT; proxy_set_header Host \$host; }
}
CONF
  ln -sf /etc/nginx/sites-available/davidzakirov /etc/nginx/sites-enabled/davidzakirov
  nginx -t && systemctl reload nginx
  command -v certbot >/dev/null && certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect || true
  echo "site:  https://$DOMAIN"
else
  echo "site:  http://$(curl -s -4 ifconfig.me || hostname -I | awk '{print $1}'):$PORT"
fi
echo "admin: same URL + /admin"
