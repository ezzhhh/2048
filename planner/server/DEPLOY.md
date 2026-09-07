# Свой сервер, без git, все устройства

После первого входа с телефона откроется **мастер настройки**: свой пароль, фокус, импорт backlog. Дальше пункт «Настройка» в шапке — смена пароля и повторный импорт.

Источник правды — SQLite на **вашем** сервере. Git не нужен: ни для синхронизации, ни для доступа. ПК, ноут и телефон открывают один адрес.

Доступ только у того, кто знает логин и пароль. Пароль живёт в `.env` на сервере, не в репозитории.

## 1. Скопировать папку на сервер

С вашего ПК (флешка, scp, rsync — что угодно, не git):

```bash
scp -r planner user@SERVER:/opt/planer/planner
```

Нужны: `planner/engine.py`, `planner/server/`, `planner/__init__.py`.

## 2. Пароль

```bash
cd /opt/planer/planner/server
cp .env.example .env
nano .env
```

Задайте длинный `PLANER_PASSWORD` и случайный `PLANER_SECRET` (от 16 символов). Логин по умолчанию `me`.

## 3. Запуск Docker

Из каталога, где лежит весь пакет `planner` (родитель `server/`):

```bash
cd /opt/planer
docker compose -f planner/server/docker-compose.yml up -d --build
```

Приложение слушает только `127.0.0.1:8787` — с интернета его не видно, пока не поставите прокси.

Без Docker:

```bash
python3 -m venv /opt/planer/venv
/opt/planer/venv/bin/pip install -r planner/server/requirements.txt
export $(grep -v '^#' planner/server/.env | xargs)
export PLANER_DATA=/opt/planer/data/planer.sqlite
/opt/planer/venv/bin/uvicorn planner.server.app:app --host 127.0.0.1 --port 8787
```

Запускайте из `/opt/planer`, чтобы импорт `planner` находился.

## 4. Телефон и ноут с интернета

Нужен домен на ваш сервер и HTTPS. Пример Caddy — `Caddyfile.example`. После этого в `.env` поставьте `PLANER_HTTPS=1` и перезапустите контейнер.

На телефоне: Safari / Chrome → «На экран Домой». Это обычный сайт с паролем, отдельное приложение не нужно.

По локальной сети без домена можно открыть `http://IP-сервера:8787`, но тогда в compose смените порт на `0.0.0.0:8787:8787` и не выставляйте это в интернет без HTTPS.

## 5. Бэкап

Файл базы: том Docker `planer_data` или `PLANER_DATA`. Копируйте sqlite раз в день — этого достаточно, git не подключайте.

## Что не делается

- Нет общего доступа и регистрации.
- Нет Telegram, пока вы явно не скажете.
- Публичный GitHub не хранит вашу доску.
