# Queue And Limits

## Purpose

Queue protection keeps STL Master usable during beta testing. It limits concurrent work, caps queued jobs, and gives premium users higher priority without interrupting already running jobs.

## Access levels

| Access level | Active jobs | Queued jobs | Upload attempts | Upload size |
| --- | ---: | ---: | ---: | ---: |
| Free / no code | 1 | 2 | 5 per hour | 100 MB |
| Early Access | 1 | 3 | 15 per hour | 100 MB |
| Premium | 2 | 10 | 50 per hour | 300 MB |

Global limits:

- maximum queue size: 50 jobs;
- worker reads priority queues in this order: `premium`, `early_access`, `free`, legacy queue;
- already running jobs are not preempted;
- heavy jobs are marked in metadata for future capacity planning.

## User status

`GET /api/v1/jobs/{job_id}` includes:

```json
{
  "queue_position": 4,
  "queue_size": 12,
  "estimated_wait_seconds": 360,
  "priority": "premium",
  "access_level": "premium"
}
```

The frontend shows queue position, total queue size, estimated wait, and priority while a job is queued.

## Upload protection

Before accepting a file, backend checks:

- global queue size;
- queued and processing jobs for the access-code user or IP;
- upload rate limit;
- beta upload size limit.

When the per-user limit is reached, backend returns `429` with:

```text
Сейчас у вас уже есть задача в обработке. Дождитесь завершения или используйте Premium-доступ.
```

When the global queue is full, backend returns:

```text
Сервер сейчас перегружен. Попробуйте позже.
```

## Admin queue dashboard

Admin page `/admin` has the “Очередь” tab.

It shows:

- queued jobs;
- processing jobs;
- completed and failed jobs for the last 24 hours;
- average processing time;
- load grouped by access level;
- job list with operations, priority, size, duration, and queue position.

## Cancel job

Admin endpoint:

```bash
POST /api/v1/admin/jobs/{job_id}/cancel
```

Behavior:

- queued job: removed from Redis queues and marked `cancelled`;
- processing job: marked `cancel_requested=true`;
- worker checks `cancel_requested` between processing stages.

Example:

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_SESSION" \
  http://127.0.0.1:8000/api/v1/admin/jobs/JOB_ID/cancel
```

## Operational notes

- Redis is still the queue source of truth.
- Legacy queue `stl:jobs` remains supported for older queued jobs.
- Localhost smoke tests are not blocked by hourly upload rate limits.
- Premium priority applies to waiting jobs only; running work is not stopped.
