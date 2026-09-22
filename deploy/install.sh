#!/usr/bin/env bash
# Ubuntu serverga o'rnatish (Docker'siz). Loyiha /opt/quizbot da bo'lishi kerak.
#   sudo bash deploy/install.sh
set -euo pipefail

APP_DIR=/opt/quizbot
APP_USER=quizbot

cd "$APP_DIR"

echo "==> Tizim paketlari"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx

echo "==> Foydalanuvchi: $APP_USER"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

if [ ! -f .env ]; then
  cp .env.example .env
  SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(50))")
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$SECRET|; s|^DJANGO_DEBUG=.*|DJANGO_DEBUG=False|" .env
  echo "!! .env yaratildi. BOT_TOKEN va DJANGO_ALLOWED_HOSTS ni to'ldirib, skriptni qayta ishga tushiring:"
  echo "   nano $APP_DIR/.env"
  exit 1
fi

echo "==> Virtual muhit va kutubxonalar"
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

echo "==> Migratsiya va statik fayllar"
mkdir -p media staticfiles
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput -v0

chown -R "$APP_USER":www-data "$APP_DIR"
chmod 640 .env

echo "==> systemd servislar"
cp deploy/quizbot-web.service deploy/quizbot-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now quizbot-web quizbot-bot
systemctl restart quizbot-web quizbot-bot

echo "==> nginx"
if [ ! -f /etc/nginx/sites-available/quizbot ]; then
  cp deploy/nginx-quizbot.conf /etc/nginx/sites-available/quizbot
  ln -sf /etc/nginx/sites-available/quizbot /etc/nginx/sites-enabled/quizbot
fi
nginx -t && systemctl reload nginx

echo
echo "Tayyor. Keyingi qadamlar:"
echo "  sudo -u $APP_USER $APP_DIR/venv/bin/python $APP_DIR/manage.py createsuperuser"
echo "  sudo -u $APP_USER $APP_DIR/venv/bin/python $APP_DIR/manage.py seed_demo   # ixtiyoriy"
echo "  journalctl -u quizbot-bot -f      # bot loglari"
