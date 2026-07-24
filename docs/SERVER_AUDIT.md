# STL Master Server Audit

Дата аудита: 2026-06-13

## Краткий итог

- Корневой раздел `/dev/sda1`: 79G всего, 73G занято, 5.9G свободно, 93%.
- Основные источники занятого места:
  - Docker volumes STL Master: `/data/results` 15G, `/data/uploads` 5.3G.
  - Docker build cache: 1.664G.
  - Dangling Docker images: несколько старых worker/frontend/backend образов.
  - `/var/log`: 7.6G по `du`, крупнейшие каталоги `/var/log/journal` 4.1G и `/var/log/mtproxy_bot` 1.3G.
- Redis data: 5.3M.
- Project code in `/home/codex/projects/vk-stl-master`: около 27M без Docker volumes.
- Активных job в Redis на момент аудита нет.

## Таблица очистки

| Каталог / ресурс | Размер | Можно удалить | Причина |
|---|---:|---|---|
| `/data/results` | 15G | Частично | 303 job-папки с результатами smoke/dev обработок. Удалять только неактивные job или job, связанные с test artifacts. |
| `/data/uploads` | 5.3G | Частично | 303 job-папки с исходными upload STL. Удалять только неактивные job или job, связанные с test artifacts. |
| `tests/results` | 1.7M | Да | JSON/listing артефакты smoke-тестов. Не являются исходными тестовыми моделями. |
| Docker dangling images | ~несколько GB shared layers | Да | Старые untagged images после rebuild. Активные контейнеры используют tagged latest images. |
| Docker build cache | 1.664G | Да | Восстанавливается при следующих build, не содержит пользовательских данных. |
| Exited containers | ~35M writable layer | Да, но не обязательно | 5 контейнеров 9-месячной давности, не относятся к текущему compose. |
| `__pycache__`, `*.pyc` в проекте | 292K | Да | Генерируемые Python cache files. |
| `/var/log/journal` | 4.1G по `du` | Позже | Системные журналы. Нужна отдельная политика journal retention. |
| `/var/log/mtproxy_bot` | 1.3G | Позже | Логи стороннего сервиса, не часть STL Master. |
| `vk-stl-master_redis-data` | 5.58M | Нет | Redis volume текущего проекта. |
| `vk-stl-master_uploads-data` | 5.603G | Не удалять volume | Volume нужен backend/worker. Можно чистить только отдельные job-папки. |
| `vk-stl-master_results-data` | 15.94G | Не удалять volume | Volume нужен download/results. Можно чистить только отдельные job-папки. |
| `test-data/Geely_atlas_pro.stl` | часть 25M test-data | Нет | Основная реальная тестовая модель. |
| `README.md`, `docs`, `tests`, source code | <1M без test-data | Нет | Код и документация проекта. |

## Безопасно удалить сейчас

- `tests/results/*`, кроме сводных файлов, если они нужны.
- Job folders в `/data/uploads` и `/data/results`, которые связаны с smoke-test артефактами и не активны в Redis.
- `__pycache__` и `*.pyc` внутри проекта.
- Dangling Docker images.
- Docker builder cache.

## Рекомендуется очистить позже

- `/var/log/journal`: настроить лимит, например `SystemMaxUse=512M`, затем `journalctl --vacuum-size=512M`.
- `/var/log/mtproxy_bot`: настроить logrotate или архивирование.
- Exited containers 9-месячной давности: можно удалить через `docker container prune`, если точно не нужны для диагностики старого окружения.

## Не трогать

- Docker volumes целиком.
- Redis volume.
- `test-data/Geely_atlas_pro.stl`.
- `test-data` целиком без отдельного решения.
- Исходный код, README, docs, tests.
- Активные или queued jobs.

## Детали аудита

### Disk

```text
/dev/sda1 79G total, 73G used, 5.9G available, 93%
/var/log 7.6G
/usr 6.9G
/var 8.0G
/home 103M
```

### Docker

```text
vk-stl-master_results-data 15.94G
vk-stl-master_uploads-data 5.603G
vk-stl-master_redis-data 5.58M
buildx_buildkit_mybuilder0_state 1.797G
Build cache 1.664G
Stopped containers: 5 old containers from 9 months ago
```

### STL Master data

```text
/data/uploads 5.3G, 303 job folders, 303 files
/data/results 15G, 303 job folders, 2951 files
tests/results 1.7M, 276 files
test-data 25M, 7 files
Jobs older than 30 days: 0
ZIP older than 30 days: 0
STL older than 30 days: 0
```

### Python/cache/logs

```text
__pycache__ count: 2
*.pyc count: 2
Python cache total: 292K
/home/codex/.npm 12K
Redis /data 5.3M
/var/log 7.6G
journalctl --disk-usage reported 111.6M for accessible active/archived journals
```

## Выполненная безопасная очистка

Выполнено после формирования отчёта:

- Удалены smoke-test result files из `tests/results`, кроме служебных сводных файлов.
- По `job_id`, найденным в `tests/results`, удалены неактивные job folders из `/data/uploads` и `/data/results`.
- Удалены `__pycache__` внутри проекта.
- Выполнен `docker image prune -f` для dangling images.
- Выполнен `docker builder prune -af` для build cache.

Не удалялись:

- Docker volumes целиком.
- Redis volume.
- `test-data`, включая `Geely_atlas_pro.stl`.
- README, docs, tests, source code.
- Активные/queued jobs. На момент очистки активных Redis job keys не было.

## Состояние после очистки

```text
/dev/sda1 79G total, 58G used, 22G available, 74%
Docker images: 1.88G
Docker build cache: 0B
Docker local volumes: 8.988G
/data/uploads: 1.8G, 119 job folders, 119 files
/data/results: 5.0G, 119 job folders, 1227 files
tests/results: 48K
test-data: 25M
docs: 20K
```

Освобождено примерно 16G на корневом разделе: свободное место выросло с 5.9G до 22G.

## Что ещё можно освободить вручную

- `/var/log` остаётся крупнейшим системным каталогом: около 7.5G.
- `/var/log/journal` по `du` занимает около 4.1G. Рекомендуется отдельно настроить retention systemd-journald и выполнить vacuum только после подтверждения.
- `/var/log/mtproxy_bot` занимает около 1.3G. Это не часть STL Master, нужна отдельная политика logrotate/архивации.
- В Docker остаются старые exited containers 9-месячной давности. Их можно удалить через `docker container prune`, если они точно не нужны для диагностики старого окружения.
