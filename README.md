# Telegram Test Bot + Admin panel

Telegram bot foydalanuvchini ro'yxatdan o'tkazadi (ism, familiya, telefon), test tilini so'raydi (RU/EN),
faol paketlardan birini **tasodifiy** tanlaydi va savollarni `Part 1 — Mathematics → Part 2 — English →
Part 3 — IQ / Logical Reasoning` tartibida beradi. Javob bosilishi bilan savol xabari o'chadi, keyingisi chiqadi.
Test yakunida foydalanuvchi o'z natijasini ko'radi, admin esa hamma natijani panelda ko'radi.

## Texnologiyalar
Django 5 · aiogram 3 · SQLite yoki PostgreSQL · gunicorn + nginx + systemd (Docker kerak emas)

## Tuzilma
```
config/            Django sozlamalari, URL'lar
quiz/              Modellar, test logikasi (services.py), seed_demo komandasi, testlar
panel/             Alohida admin panel (/panel/): paketlar, bo'limlar, savollar, natijalar, Excel
bot/               Telegram bot (aiogram 3): handlers, matnlar, klaviaturalar, runbot komandasi
deploy/            systemd servislar, nginx konfiguratsiya, install.sh / update.sh
run_local.sh       Lokalda panel + botni bitta buyruq bilan ishga tushirish
```

## Lokal ishga tushirish (Windows / Git Bash)
Talab: Python 3.11+.

Eng oson yo'l:
```bash
bash run_local.sh        # 1-marta venv yaratadi va .env nusxalaydi — BOT_TOKEN ni yozib, qayta ishga tushiring
```
So'ng boshqa terminalda admin yarating va demo savollarni qo'shing:
```bash
venv/Scripts/python manage.py createsuperuser
venv/Scripts/python manage.py seed_demo      # 2 ta demo paket (har birida 15 ta savol)
```
Panel: http://127.0.0.1:8000/panel/ — bot esa `run_local.sh` terminalida ishlaydi.

Qo'lda (ikki terminalda):
```bash
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env                 # BOT_TOKEN
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver           # 1-terminal
python manage.py runbot              # 2-terminal
```
Baza: `.env` da `POSTGRES_*` qatorlari izohda bo'lsa — `db.sqlite3` ishlatiladi.

## Serverga o'rnatish (Ubuntu, Docker'siz)
```bash
scp quizbot.zip user@server:/tmp/
ssh user@server
sudo unzip /tmp/quizbot.zip -d /opt/          # -> /opt/quizbot
cd /opt/quizbot
sudo bash deploy/install.sh                   # 1-marta .env yaratadi va to'xtaydi
sudo nano .env                                # BOT_TOKEN, DJANGO_ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
sudo nano deploy/nginx-quizbot.conf           # server_name — domen yoki IP
sudo bash deploy/install.sh                   # venv, migratsiya, systemd, nginx
sudo -u quizbot venv/bin/python manage.py createsuperuser
sudo -u quizbot venv/bin/python manage.py seed_demo      # ixtiyoriy
```
Natijada ikki servis ishlaydi:
- `quizbot-web` — gunicorn (127.0.0.1:8000), oldida nginx (80-port)
- `quizbot-bot` — Telegram bot (long polling, webhook/domen shart emas)

Foydali buyruqlar:
```bash
sudo systemctl status quizbot-web quizbot-bot
sudo journalctl -u quizbot-bot -f             # bot loglari
sudo systemctl restart quizbot-bot
sudo bash deploy/update.sh                    # kod yangilangandan keyin
```
SSL: `sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d test.example.uz`,
so'ng `.env` da `CSRF_TRUSTED_ORIGINS=https://test.example.uz`.

PostgreSQL kerak bo'lsa: `sudo apt install postgresql`, baza va foydalanuvchi yarating, `.env` dagi
`POSTGRES_*` qatorlarini oching (`POSTGRES_HOST=localhost`) va `sudo bash deploy/update.sh`.

## Admin panel (`/panel/`)
- **Bosh sahifa** — yakunlangan testlar, bugungi, jarayondagi, o'rtacha natija, bo'limlar bo'yicha o'rtacha.
- **Paketlar** — yaratish, tahrirlash, faollashtirish/o'chirish, nusxa olish, bo'lim ichida savollarni
  aralashtirish opsiyasi. Har bir paketga xohlagancha bo'lim qo'shish mumkin — nomi, ko'rsatmasi va
  ketma-ketligi (↑/↓ tugmalari bilan) to'liq admin nazoratida.
- **Bo'limlar** — erkin nom (RU/EN sarlavha), tartib va ko'rsatma (bo'limning birinchi savolida chiqadi).
- **Savollar** — RU/EN matn, ixtiyoriy rasm, 2–10 ta variant (qo'shish/olib tashlash), aynan bitta to'g'ri javob.
- **Natijalar** — F.I.Sh., telefon, Telegram ID, til, paket, umumiy natija, boshlangan/tugagan vaqt;
  qidiruv va filtrlar (paket, til, holat, sana, min %), saralash. Har bir natija sahifasida paketning
  o'z bo'limlari bo'yicha batafsil taqsimot ko'rsatiladi.
- **Natija sahifasi** — javoblar varaqasi (har bir savol yashil/qizil doira) va har bir savolda tanlangan javob.
- **Foydalanuvchilar** — ro'yxat va qidiruv.
- Zaxira sifatida standart Django admin: `/django-admin/`.

## Muhim qoidalar
- Test boshlanganda savollar ro'yxati sessiyaga "muzlatiladi": admin keyin savolni o'zgartirsa ham boshlangan test buzilmaydi.
- Javobi bor savol o'chirilmaydi — nofaol qilinadi. Natijasi bor paketni o'chirib bo'lmaydi — nofaol qiling.
- `ALLOW_RETAKE=False` bo'lsa, testni tugatgan foydalanuvchi `/start` bossa, oldingi natijasini ko'radi.
  Admin natijani o'chirsa, u qayta topshira oladi. `True` bo'lsa — cheklovsiz.
- Bot qayta ishga tushsa ham tugallanmagan test yo'qolmaydi: `/start` joriy savoldan davom ettiradi.
- Tugmani ikki marta bosish yoki eski savol tugmasi hisobga olinmaydi; boshqa foydalanuvchining sessiyasiga javob berib bo'lmaydi.

## Bot komandalar
`/start` — testni boshlash yoki davom ettirish · `/result` — oxirgi natija · `/help`

## Testlar
```bash
python manage.py test quiz
```
