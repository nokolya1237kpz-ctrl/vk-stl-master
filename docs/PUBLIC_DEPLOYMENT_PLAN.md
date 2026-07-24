# STL Master: Public Web Deployment Plan

Дата аудита: 2026-06-16

## Текущее состояние

| Область | Факт |
| --- | --- |
| Frontend container | `stl-master-frontend`, опубликован как `0.0.0.0:3000->80/tcp` |
| Backend container | `stl-master-backend`, опубликован как `0.0.0.0:8000->8000/tcp` |
| Redis container | `stl-master-redis`, без `ports` в `docker-compose.yml`; доступен только внутри Docker-сети как `redis:6379` |
| Worker container | `stl-master-worker`, наружу не опубликован |
| Backend health | `GET http://localhost:8000/health` возвращает `{"status":"ok"}` |
| Frontend health | `curl -I http://localhost:3000` возвращает `HTTP/1.1 200 OK` |
| Beta mode | Включён: `beta_mode=true` |
| Beta upload limit | 100 МБ, абсолютный backend safety limit 500 МБ |

## Открытые порты

По `ss -tulpn` на момент аудита:

| Порт | Состояние | Комментарий |
| --- | --- | --- |
| `80` | слушает `0.0.0.0:80` | занят системным nginx |
| `443` | слушает `*:443` | на сервере есть HTTPS listener |
| `3000` | слушает `0.0.0.0:3000` и `[::]:3000` | frontend Docker опубликован напрямую наружу |
| `8000` | слушает `0.0.0.0:8000` и `[::]:8000` | backend Docker опубликован напрямую наружу |
| `6379` | слушает `127.0.0.1:6379` и `[::1]:6379` | Redis не опубликован Docker Compose наружу; локальный listener не доступен с внешних интерфейсов |

## Nginx

Nginx установлен и запущен:

- версия: `nginx/1.24.0 (Ubuntu)`;
- сервис: `active (running)`;
- включённый site: `/etc/nginx/sites-enabled/3d-api`;
- текущий enabled site использует домен `3dcalk.freedynamicdns.net`, порт `80` для redirect и `8443 ssl` для существующего сервиса.

Для публикации STL Master нужен отдельный nginx server block под новый домен. Не рекомендуется отдавать beta напрямую через `:3000` и `:8000`.

## Certbot

Certbot установлен:

```text
certbot 2.9.0
```

Для домена STL Master нужно выпустить отдельный сертификат после того, как DNS A-record домена будет указывать на сервер.

## Firewall

Статус `ufw` не удалось получить без интерактивного sudo:

```text
sudo: a terminal is required to read the password
```

Перед публикацией нужно проверить firewall под root/sudo и явно разрешить только нужные публичные порты:

- `80/tcp`
- `443/tcp`

Порты `3000`, `8000`, `6379` не должны быть доступны публично после настройки nginx.

## Docker Compose и Redis

Redis в `docker-compose.yml` не имеет секции `ports`. Это правильно: backend и worker используют Redis внутри Docker-сети через:

```text
REDIS_URL=redis://redis:6379/0
```

Риск Redis снаружи по compose не найден. Отдельный локальный listener `127.0.0.1:6379` нужно оставить закрытым для внешних интерфейсов.

## Что нужно сделать для домена

1. Настроить DNS:
   - создать `A` record домена на IP сервера;
   - дождаться распространения DNS.
2. Создать nginx config для STL Master:
   - `server_name <domain>`;
   - `location /` proxy на `http://127.0.0.1:3000`;
   - `location /api/` proxy на `http://127.0.0.1:8000`;
   - `client_max_body_size 100M`;
   - proxy timeouts не меньше 300 секунд для загрузки STL.
3. Выпустить SSL:
   - `certbot --nginx -d <domain>`;
   - проверить auto-renew.
4. Закрыть прямой доступ к Docker-портам:
   - либо изменить compose ports на localhost bindings:
     - `127.0.0.1:3000:80`
     - `127.0.0.1:8000:8000`
   - либо закрыть `3000` и `8000` firewall-ом.
5. Проверить:
   - `https://<domain>/`;
   - `https://<domain>/api/v1/status`;
   - upload STL до 100 МБ;
   - ZIP и отдельные download endpoints.

## Basic Auth для закрытой beta

До публичного запуска beta нужно закрыть домен Basic Auth на уровне nginx.

Пример:

```nginx
server {
    listen 443 ssl http2;
    server_name stl.example.com;

    auth_basic "STL Master Beta";
    auth_basic_user_file /etc/nginx/.htpasswd-stl-master;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_connect_timeout 120s;
    }
}
```

Создание пароля:

```bash
sudo apt-get install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd-stl-master beta
sudo nginx -t
sudo systemctl reload nginx
```

## Риски

| Риск | Уровень | Что сделать |
| --- | --- | --- |
| Frontend и backend сейчас доступны напрямую на `:3000` и `:8000` | Высокий | Перед публикацией закрыть прямые порты через localhost binding или firewall |
| Firewall status не проверен | Высокий | Проверить `sudo ufw status` под root и разрешить только `80/443` |
| Beta без Basic Auth может получить посторонний трафик | Высокий | Включить Basic Auth на домене до приглашения тестировщиков |
| Upload больших STL через nginx может падать по `client_max_body_size` или timeout | Средний | Поставить `client_max_body_size 100M` и proxy timeouts |
| Существующий nginx site уже использует `80` и `8443` | Средний | Добавить отдельный server block для нового домена, не ломая текущий `3d-api` |
| Docker volumes с STL могут расти | Средний | Оставить регулярный запуск `./scripts/cleanup-test-artifacts.sh 24` |
| Feedback и job results содержат пользовательские файлы | Средний | Предупредить beta-тестировщиков не отправлять конфиденциальные модели |

## Готовность к публикации

Сервер технически почти готов к размещению домена: nginx и certbot установлены, контейнеры работают, health checks успешны, Redis не опубликован наружу через Docker Compose.

Но сервер ещё не готов к публичной beta-публикации без дополнительной настройки, потому что frontend/backend доступны напрямую на публичных портах `3000` и `8000`, а firewall status не подтверждён.

## Следующий шаг

1. Получить домен и направить DNS на сервер.
2. Создать nginx server block под домен STL Master.
3. Выпустить SSL через certbot.
4. Включить Basic Auth.
5. Закрыть публичный доступ к `3000` и `8000`.
6. Проверить домен smoke-тестом через HTTPS.
