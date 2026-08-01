# SunneKatha production deployment

This guide describes a provider-neutral container deployment and an AWS
reference architecture. The container does not depend on ECS, EKS, EC2, or any
specific deployment controller.

## Runtime architecture

Deploy one immutable image with four distinct process roles:

| Role | Container command | Replicas |
| --- | --- | --- |
| Web API | `web` | Two or more |
| Celery worker | `worker` | One or more |
| Celery Beat | `beat` | Exactly one |
| Release migration | `migrate` | One short-lived task per release |

The entrypoint also supports `check` for `manage.py check --deploy`. Web
containers intentionally do not run migrations or collect static assets.
Static assets are collected into the image at build time and served through
WhiteNoise with immutable hashed filenames.

Gunicorn handles `SIGTERM`, stops accepting new work, and allows in-flight
requests up to `GUNICORN_GRACEFUL_TIMEOUT_SECONDS`. The deployment platform
should use a termination grace period longer than that value, normally 60
seconds. Celery workers also receive `SIGTERM`; visibility timeout, late
acknowledgement, and worker-loss rejection allow interrupted tasks to return to
the broker.

## Build and release

Build from `backend/`:

```bash
docker build --pull --tag sunnekatha-api:${APP_VERSION} .
docker run --rm --env-file production.env sunnekatha-api:${APP_VERSION} check
```

Tag images with an immutable commit SHA or release identifier. Do not deploy
`latest` as the only recoverable reference.

The image build uses `config.settings.build` only for `collectstatic`. Runtime
processes default to `config.settings.production`.

### Migration startup strategy

Run migrations as a single release task after taking a database snapshot and
before shifting traffic:

```bash
docker run --rm --env-file production.env \
  sunnekatha-api:${APP_VERSION} migrate
```

Do not run migrations in every web replica. Concurrent migration attempts can
lock tables, create startup races, and make autoscaling unsafe.

Use expand-and-contract migrations:

1. Add nullable columns, new tables, or compatible indexes.
2. Deploy code that can read both old and new representations.
3. Backfill asynchronously where necessary.
4. Switch reads and writes in a later release.
5. Remove obsolete columns only after the rollback window closes.

Use PostgreSQL concurrent indexes for large live tables when Django's atomic
migration behavior is adjusted deliberately. Review any table rewrite or lock
before release.

## Required production environment

Inject secrets from the deployment platform's secret manager. Never put them
in the image, task definition source, or repository.

Required values include:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
APP_VERSION=2026.07.23+commitsha
STATIC_ROOT=/var/www/sunnekatha/static
DJANGO_SECRET_KEY=<at-least-50-random-characters>
DJANGO_ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
DRF_ANON_THROTTLE_RATE=1000/hour
DRF_USER_THROTTLE_RATE=5000/hour

DATABASE_URL=postgresql://user:password@database:5432/sunnekatha
DATABASE_CONN_MAX_AGE=60
DATABASE_CONNECT_TIMEOUT_SECONDS=5
DATABASE_SSL_MODE=require

REDIS_URL=rediss://cache:6379/1
CELERY_BROKER_URL=rediss://cache:6379/2
CELERY_RESULT_BACKEND=rediss://cache:6379/3

USE_S3_STORAGE=true
AWS_S3_REGION_NAME=us-east-1
AWS_S3_AUDIO_BUCKET_NAME=<private-audio-bucket>
AWS_S3_COVER_BUCKET_NAME=<private-cover-bucket>
AWS_CLOUDFRONT_DOMAIN=media.example.com
CLOUDFRONT_MEDIA_DOMAIN=audio.example.com
CLOUDFRONT_KEY_PAIR_ID=<trusted-key-id>
CLOUDFRONT_PRIVATE_KEY=<secret-private-key>
```

Production validation rejects weak/default secrets, wildcard hosts, non-HTTPS
CORS/CSRF origins, non-PostgreSQL databases, custom S3 endpoints, missing media
configuration, and plaintext Redis URLs. `ALLOW_INSECURE_REDIS=true` exists for
private non-TLS environments but is not recommended.

For certificate verification beyond encrypted transport, set
`DATABASE_SSL_MODE=verify-full` and include the appropriate PostgreSQL root
certificate in the runtime trust configuration.

## Proxy and HTTPS

Terminate public TLS at a trusted reverse proxy or load balancer. It must:

- remove client-provided forwarding headers;
- set `X-Forwarded-Proto: https`;
- preserve or replace `Host` with an allowed hostname;
- route only to private container addresses;
- drain targets before sending `SIGTERM`.

`TRUST_X_FORWARDED_PROTO=true` enables Django's secure-proxy header. Keep
`USE_X_FORWARDED_HOST=false` unless the proxy validates and replaces the host.

Gunicorn trusts forwarded headers only from
`GUNICORN_FORWARDED_ALLOW_IPS`. For load balancers with changing source
addresses, `*` may be used only when security groups or equivalent network
policy prevent all direct client access to the container port.

Set `DRF_NUM_PROXIES` to the exact number of trusted reverse proxies between
the client and Django (default `1`). DRF uses this value to derive throttle
identity from `X-Forwarded-For`; an incorrect value can group unrelated clients
or permit spoofed forwarding entries. Production rejects values outside 1–10.

## FFmpeg

The runtime image includes FFmpeg and ffprobe. Verify their versions during
image qualification:

```bash
docker run --rm sunnekatha-api:${APP_VERSION} ffmpeg -version
docker run --rm sunnekatha-api:${APP_VERSION} ffprobe -version
```

Audio processing is not currently implemented. FFmpeg availability alone does
not make confirmed uploads publishable; keep ingestion operationally disabled
or manually controlled until the processing task and promotion workflow are
implemented.

## Health and observability

- `/api/v1/health/` is liveness-only and performs no dependency I/O.
- `/api/v1/readiness/` verifies PostgreSQL and Redis.
- `/api/v1/version/` returns the immutable deployed `APP_VERSION`.

Use liveness to restart a wedged process and readiness for load-balancer target
registration. Do not use readiness as liveness: a temporary database or cache
incident should remove a target from traffic, not restart every application
container.

Django emits JSON logs to stdout in production. Gunicorn access and error logs
also use stdout/stderr. Include release, service, task/container, and trace
metadata in the platform log collector. Never log JWTs, signed CloudFront URLs,
upload policies, database URLs, or secret values.

Alert on sustained readiness failures, elevated 5xx responses, authentication
failure spikes, queue depth, worker task failures, database saturation,
replication/backup failures, and S3/CloudFront authorization errors.

## AWS reference deployment

A typical AWS deployment uses:

- an Application Load Balancer with ACM-managed HTTPS;
- ECS/Fargate or EKS for web, worker, Beat, and release tasks;
- Amazon RDS for PostgreSQL with encryption, Multi-AZ, and automated backups;
- ElastiCache for Redis with in-transit encryption and authentication;
- private S3 buckets with Block Public Access and versioning;
- CloudFront with Origin Access Control and trusted key groups;
- Secrets Manager or SSM Parameter Store for runtime secrets;
- CloudWatch Logs and alarms;
- IAM workload roles instead of static AWS access keys.

Place application tasks, RDS, and Redis in private subnets. Permit the ALB to
reach only the web task port, application security groups to reach database and
Redis ports, and controlled egress to AWS APIs. Run Beat as exactly one service
replica to prevent duplicated schedules.

The workload IAM policy should be restricted to the documented media prefixes.
CloudFront—not S3—serves audio. Keep the audio bucket private and never expose
AWS credentials or raw private object paths.

## Deployment checklist

- [ ] CI passes checks, migrations, lint, coverage, and OpenAPI validation.
- [ ] Image is tagged immutably and vulnerability-scanned.
- [ ] `APP_VERSION` matches the image/release.
- [ ] Production environment validation passes with `check`.
- [ ] Secrets come from a managed secret store and are not in image layers.
- [ ] RDS automated backups, retention, encryption, and restore testing exist.
- [ ] S3 Block Public Access, encryption, versioning, lifecycle, and OAC exist.
- [ ] Redis TLS, authentication, eviction policy, and capacity are reviewed.
- [ ] CORS, CSRF, allowed hosts, proxy header replacement, and HSTS are correct.
- [ ] Database migration is reviewed for locks and backward compatibility.
- [ ] A fresh pre-deploy database snapshot is available.
- [ ] The one-off migration task succeeds before traffic shifts.
- [ ] Web has at least two healthy replicas across failure domains.
- [ ] Exactly one Beat replica and at least one worker are healthy.
- [ ] Liveness, readiness, version, logs, metrics, and alarms are verified.
- [ ] A smoke test covers login, homepage, free playback, and premium denial.

## Backup checklist

- [ ] Enable RDS automated backups and point-in-time recovery.
- [ ] Take a manual snapshot before destructive or high-lock migrations.
- [ ] Encrypt snapshots and restrict snapshot sharing.
- [ ] Enable S3 versioning and appropriate lifecycle retention.
- [ ] Replicate irreplaceable originals to a separate region/account if required.
- [ ] Export and protect infrastructure definitions and non-secret configuration.
- [ ] Record secret rotation procedures; do not copy plaintext secrets into backups.
- [ ] Treat Redis as rebuildable cache/broker state, not a durable source of truth.
- [ ] Test database and media restoration on a schedule.
- [ ] Record recovery-point and recovery-time objectives and restore-test evidence.

## Rollback checklist

- [ ] Stop traffic shifting and retain the failed image and logs for diagnosis.
- [ ] Confirm whether the migration is backward-compatible with the prior image.
- [ ] Redeploy the previous immutable web and worker image.
- [ ] Keep exactly one compatible Beat instance running.
- [ ] Do not reverse a destructive migration without an explicit reviewed plan.
- [ ] Restore RDS to a new instance for irreversible corruption or data loss.
- [ ] Repoint secrets/endpoints only after restored data is verified.
- [ ] Invalidate CloudFront only when object behavior requires it; hashed static
      assets normally need no invalidation.
- [ ] Verify health, readiness, version, authentication, playback, queues, and jobs.
- [ ] Resume traffic gradually and monitor errors, latency, and worker failures.
- [ ] Document the incident and required forward fix.
