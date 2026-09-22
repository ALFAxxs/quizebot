#!/usr/bin/env bash
# Lokal ishga tushirish (Windows Git Bash / Linux / macOS):  bash run_local.sh
# Panel: http://127.0.0.1:8000/panel/   Bot: shu terminalda ishlaydi. To'xtatish: Ctrl+C
set -e
cd "$(dirname "$0")"

if [ -d venv/Scripts ]; then PY=venv/Scripts/python; elif [ -d venv/bin ]; then PY=venv/bin/python; else
  echo "==> venv yaratilmoqda"
  python -m venv venv 2>/dev/null || python3 -m venv venv
  if [ -d venv/Scripts ]; then PY=venv/Scripts/python; else PY=venv/bin/python; fi
  $PY -m pip install --upgrade pip -q
  $PY -m pip install -r requirements.txt -q
fi

[ -f .env ] || { cp .env.example .env; echo "!! .env yaratildi — BOT_TOKEN ni yozing va qayta ishga tushiring."; exit 1; }

$PY manage.py migrate --noinput -v0
$PY manage.py runserver 127.0.0.1:8000 &
WEB_PID=$!
trap "kill $WEB_PID 2>/dev/null" EXIT
$PY manage.py runbot
