# STL Master: Public Beta Deployment

Дата подготовки: 2026-06-17

Домен beta: `app.stlmaster.online`

## Статус

Подготовка выполнена частично. DNS уже указывает на текущий сервер, но фактическое применение nginx/Basic Auth/SSL остановлено, потому что пользователь `codex` не имеет passwordless sudo:

```text
sudo: a password is required
```

Без root/sudo нельзя безопасно записать `/etc/nginx/sites-available/stl-master-beta`, создать `/etc/nginx/.stl-master-beta.htpasswd`, выполнить `nginx -t`, `systemctl reload nginx` и `certbot --nginx`.

## DNS

Проверка:

```bash
DOMAIN="app.stlmaster.online"
dig +short "$DOMAIN"
```

Результат:

```text
194.87.201.19
```

Публичный IP сервера:

```text
194.87.201.19
```

Вывод: DNS домена `app.stlmaster.online` уже указывает на текущий сервер.

## Текущее состояние контейнеров

```text
stl-master-backend    Up  0.0.0.0:8000->8000/tcp, :::8000->8000/tcp
stl-master-frontend   Up  0.0.0.0:3000->80/tcp,   :::3000->80/tcp
stl-master-redis      Up (healthy) 6379/tcp
stl-master-worker     Up
```

Health:

```text
GET http://localhost:8000/health -> {"status":"ok"}
HEAD http://localhost:3000 -> HTTP/1.1 200 OK
```

## Открытые порты до публикации

```text
0.0.0.0:80     nginx
*:443          HTTPS listener
0.0.0.0:3000   frontend Docker, открыт наружу
0.0.0.0:8000   backend Docker, открыт наружу
127.0.0.1:6379 Redis local listener
```

Redis в `docker-compose.yml` не имеет `ports` и не открыт через Docker Compose наружу.

## Nginx и Certbot

Nginx установлен:

```text
nginx/1.24.0 (Ubuntu)
```

Nginx service активен.

Certbot установлен:

```text
certbot 2.9.0
```

Текущий enabled nginx site:

```text
/etc/nginx/sites-enabled/3d-api -> /etc/nginx/sites-available/3d-api
```

Он обслуживает другой домен `3dcalk.freedynamicdns.net`, поэтому для STL Master нужен отдельный server block.

## Подготовленный nginx config

Подготовлен файл в проекте:

```text
deploy/nginx/stl-master-beta.conf
```

Его нужно установить под root:

```bash
sudo cp /home/codex/projects/vk-stl-master/deploy/nginx/stl-master-beta.conf /etc/nginx/sites-available/stl-master-beta
sudo ln -s /etc/nginx/sites-available/stl-master-beta /etc/nginx/sites-enabled/stl-master-beta
sudo nginx -t
sudo systemctl reload nginx
```

Проксирование в конфиге:

- `/` -> `http://127.0.0.1:3000`
- `/api/` -> `http://127.0.0.1:8000/api/`
- `/health` -> `http://127.0.0.1:8000/health`

Параметры:

```nginx
client_max_body_size 120M;
proxy_read_timeout 600s;
proxy_send_timeout 600s;
proxy_connect_timeout 60s;
```

## Basic Auth

Beta должна быть закрыта Basic Auth.

Логин:

```text
beta
```

Пароль нужно сгенерировать при применении под root и не коммитить в репозиторий:

```bash
PASS="$(openssl rand -base64 24 | tr -d '=+/' | cut -c1-20)"
HASH="$(openssl passwd -apr1 "$PASS")"
printf 'beta:%s\n' "$HASH" | sudo tee /etc/nginx/.stl-master-beta.htpasswd >/dev/null
printf 'Beta password: %s\n' "$PASS"
sudo chmod 640 /etc/nginx/.stl-master-beta.htpasswd
sudo chown root:www-data /etc/nginx/.stl-master-beta.htpasswd
sudo nginx -t
sudo systemctl reload nginx
```

Пароль не записывать в этот документ.

## SSL

После установки nginx config и Basic Auth:

```bash
sudo certbot --nginx -d app.stlmaster.online
```

Проверить:

```bash
curl -I https://app.stlmaster.online
curl -u beta:PASSWORD -I https://app.stlmaster.online
curl -u beta:PASSWORD https://app.stlmaster.online/health
curl -u beta:PASSWORD https://app.stlmaster.online/api/v1/status
```

HTTP должен перенаправляться на HTTPS после certbot.

## Закрытие прямого доступа к Docker

После успешной настройки nginx/SSL нужно изменить `docker-compose.yml`, чтобы backend/frontend слушали только localhost:

```yaml
backend:
  ports:
    - "127.0.0.1:8000:8000"

frontend:
  ports:
    - "127.0.0.1:3000:80"
```

Применить:

```bash
docker-compose down
docker-compose up -d
```

Проверить:

```bash
curl -I http://127.0.0.1:3000
curl http://127.0.0.1:8000/health
ss -tulpn | grep -E ':3000|:8000'
```

Ожидаемый результат:

```text
127.0.0.1:3000
127.0.0.1:8000
```

Не должно остаться:

```text
0.0.0.0:3000
0.0.0.0:8000
```

## Как отключить beta-auth после тестирования

Удалить или закомментировать в nginx server block:

```nginx
auth_basic "STL Master Beta";
auth_basic_user_file /etc/nginx/.stl-master-beta.htpasswd;
```

Затем:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Очередь и защита сервера

Во время public beta backend защищает обработку через Redis priority queues.

Лимиты:

- free: 1 active, 2 queued, 5 upload attempts/hour, 100 MB;
- early_access: 1 active, 3 queued, 15 upload attempts/hour, 100 MB;
- premium: 2 active, 10 queued, 50 upload attempts/hour, 300 MB;
- global queue limit: 50 jobs.

Admin dashboard:

```text
/admin -> вкладка “Очередь”
```

Admin API:

```bash
curl -H "Authorization: Bearer $ADMIN_SESSION" https://app.stlmaster.online/api/v1/admin/queue
curl -X POST -H "Authorization: Bearer $ADMIN_SESSION" https://app.stlmaster.online/api/v1/admin/jobs/JOB_ID/cancel
```

Подробности: [QUEUE_AND_LIMITS.md](QUEUE_AND_LIMITS.md).

## Контрольный checklist применения

1. Получить root/sudo доступ.
2. Установить подготовленный nginx config.
3. Создать `/etc/nginx/.stl-master-beta.htpasswd`.
4. Проверить `nginx -t`.
5. Перезагрузить nginx.
6. Выпустить SSL через certbot.
7. Проверить `https://app.stlmaster.online` с Basic Auth.
8. Изменить Docker ports на `127.0.0.1`.
9. Перезапустить `docker-compose`.
10. Проверить, что `3000/8000` больше не открыты наружу.

## Текущая готовность

Сервер не готов к приглашению beta-тестировщиков до применения root-шагов.

Готово:

- DNS указывает на сервер.
- Приложение работает локально.
- Nginx установлен.
- Certbot установлен.
- Redis не открыт наружу через Docker Compose.
- Подготовлен nginx config.

Блокер:

- нет root/sudo доступа для применения nginx, Basic Auth, SSL и закрытия прямых Docker-портов.
## Admin Feedback

- Пользовательские отзывы сохраняются в `/data/results/feedback` как JSON-файлы.
- Основной интерфейс не показывает админские данные обычным пользователям.
- Админка доступна по пути `/admin`.
- На beta-домене `/admin` дополнительно закрыт backend admin password/session auth.
- Пароль администратора задаётся только через `./scripts/set-admin-password.sh`; в `.env` хранится `ADMIN_PASSWORD_HASH`, а не пароль.
- Frontend хранит admin session token только в `sessionStorage`.
- Admin endpoints принимают `Authorization: Bearer <session_token>`.
- `X-Admin-Token` оставлен только как emergency fallback для server-side curl/debug и должен быть отключён после beta.
- Admin login защищён от перебора: 5 неверных попыток за 10 минут, затем блокировка IP на 15 минут.
- Access-code пользователей хранится только как salted hash и тоже rate-limited.
- Audit log admin/security событий: `/data/results/audit/admin_actions.jsonl`.
- На beta-этапе доступ к `/admin` и `/api/v1/admin/feedback*` закрыт тем же Basic Auth, что и весь beta-домен.
- Smoke/test отзывы помечаются `is_test=true` и не входят в основную статистику реальных пользователей.
- В админке есть переключатель “Реальные / Тестовые / Все” и кнопка “Архивировать тестовые отзывы”.
- Архив тестовых отзывов находится в `/data/results/feedback_test_archive`; реальные отзывы из `/data/results/feedback` не удаляются.
- Для быстрой проверки summary нужно сначала получить admin session через `/api/v1/admin/login`, затем передать `Authorization: Bearer <session_token>`.

## Admin Auth And Premium Access

- Backend admin endpoints require `Authorization: Bearer <session_token>`.
- `ADMIN_TOKEN` remains only as an emergency server-side fallback; do not store it in code and disable it after beta.
- `ADMIN_PASSWORD_HASH`, `ADMIN_SESSION_SECRET`, and `ACCESS_CODE_SALT` must be set through server environment or `.env`.
- Beta users are stored in `/data/results/users/users.json`.
- User access codes are stored only as salted SHA-256 hashes.
- Free beta upload limit is 100 MB; premium beta upload limit is 300 MB.
- See `docs/ADMIN_ACCESS_AND_CLEANUP.md` for user management and cleanup operations.
