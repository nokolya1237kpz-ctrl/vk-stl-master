# Admin Access And Cleanup

## Admin password

Основной вход в `/admin` выполняется по admin-паролю. Пароль в открытом виде не хранится: backend принимает только PBKDF2-HMAC-SHA256 hash из `.env`.

Задать или сменить пароль:

```bash
./scripts/set-admin-password.sh
```

Скрипт:

- спросит пароль без отображения в терминале;
- запишет `ADMIN_PASSWORD_HASH` в `.env`;
- создаст `ADMIN_SESSION_SECRET`, если его ещё нет;
- создаст `ACCESS_CODE_SALT`, если его ещё нет;
- не выводит пароль в stdout.

После изменения `.env` перезапустите backend:

```bash
docker-compose up -d --build backend
```

## Admin session

Frontend `/admin` вызывает:

```text
POST /api/v1/admin/login
```

При успешном входе backend возвращает подписанный HMAC session token на 12 часов. Frontend хранит его только в `sessionStorage`, поэтому сессия исчезает после закрытия браузера.

Все admin endpoints принимают:

```text
Authorization: Bearer <session_token>
```

`ADMIN_TOKEN` можно оставить как emergency fallback для server-side curl/debug:

```text
X-Admin-Token: <token>
```

После beta его рекомендуется отключить: удалить `ADMIN_TOKEN` из `.env` и перезапустить backend.

Если `ADMIN_PASSWORD_HASH` и `ADMIN_TOKEN` не заданы, admin endpoints недоступны.

## Как зайти в админку

1. Откройте `/admin`.
2. Введите admin-пароль.
3. Session token сохранится только в `sessionStorage` браузера администратора.
4. Для выхода нажмите “Выйти из админки”.

## Anti-bruteforce

Admin login защищён rate limit через Redis:

- максимум 5 неверных попыток за 10 минут с одного IP;
- после превышения IP блокируется на 15 минут;
- ответ при блокировке: `429 Too Many Requests`;
- пароли не пишутся в логи.

Beta/premium access-code тоже защищён:

- максимум 20 неверных access-code попыток за час с одного IP;
- access-code хранится только как hash;
- сравнение выполняется через constant-time compare.

## Audit log

Admin/security события пишутся в JSONL:

```text
/data/results/audit/admin_actions.jsonl
```

События:

- `admin_login_success`;
- `admin_login_failed`;
- `admin_locked`;
- `user_created`;
- `user_premium_granted`;
- `user_blocked`;
- `user_unblocked`;
- `access_code_reset`;
- `cleanup_run`.

В audit log запрещено писать:

- admin password;
- access-code в открытом виде;
- `ADMIN_SESSION_SECRET`;
- `ADMIN_TOKEN`.

## Пользователи и premium

Пользователи beta хранятся в:

```text
/data/results/users/users.json
```

Admin может вручную создать пользователя, выдать premium, заблокировать или сбросить access code.

Access code хранится только как SHA-256 hash с `ACCESS_CODE_SALT`; открытый код показывается только в момент создания или сброса.

Лимиты:

- Free beta: 100 MB.
- Premium beta: 300 MB.
- Blocked: upload запрещён.

Premium функции на beta:

- local smoothing;
- split connectors;
- fit to bed split.

## Очередь и лимиты

Подробный контракт очереди описан в [QUEUE_AND_LIMITS.md](QUEUE_AND_LIMITS.md).

В `/admin` есть вкладка “Очередь”. Там видно:

- queued / processing jobs;
- completed / failed за последние 24 часа;
- среднее время обработки;
- нагрузку по `free`, `early_access`, `premium`;
- отдельные job с операциями, приоритетом и размером.

Отмена задачи:

- queued job удаляется из Redis queue и получает `status=cancelled`;
- processing job получает `cancel_requested=true`, worker остановит её между этапами.

Admin API:

```bash
curl -H "Authorization: Bearer $SESSION_TOKEN" http://127.0.0.1:8000/api/v1/admin/queue
curl -X POST -H "Authorization: Bearer $SESSION_TOKEN" http://127.0.0.1:8000/api/v1/admin/jobs/JOB_ID/cancel
```

## Cleanup

Cleanup API:

```bash
SESSION_TOKEN="<token from /api/v1/admin/login>"
curl -H "Authorization: Bearer $SESSION_TOKEN" http://127.0.0.1:8000/api/v1/admin/cleanup/status
curl -H "Authorization: Bearer $SESSION_TOKEN" -H "Content-Type: application/json" \
  -d '{"older_than_hours":6,"dry_run":true}' \
  http://127.0.0.1:8000/api/v1/admin/cleanup/run
```

Cleanup never removes:

- feedback;
- users;
- active queued/processing jobs;
- Docker volumes;
- Redis volume;
- `test-data/Geely_atlas_pro.stl`.

## Auto cleanup timer

Prepared files:

```text
deploy/systemd/stl-master-cleanup.service
deploy/systemd/stl-master-cleanup.timer
```

Install manually:

```bash
cp deploy/systemd/stl-master-cleanup.* /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now stl-master-cleanup.timer
systemctl list-timers | grep stl-master
```

The timer runs daily at 04:30 and logs to:

```text
/var/log/stl-master-cleanup.log
```

## Public port check

Для public beta прямые Docker ports должны слушать только localhost:

```bash
ss -tulpn | grep -E ':3000|:8000|:6379'
```

Ожидаемо:

- `127.0.0.1:3000`;
- `127.0.0.1:8000`;
- Redis не опубликован наружу.
