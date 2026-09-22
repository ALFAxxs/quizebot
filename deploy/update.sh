#!/usr/bin/env bash
# Kod yangilangandan keyin:  sudo bash deploy/update.sh
set -euo pipefail
cd /opt/quizbot
venv/bin/pip install -r requirements.txt -q
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput -v0
chown -R quizbot:www-data /opt/quizbot
systemctl restart quizbot-web quizbot-bot
echo "Yangilandi."
