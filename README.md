# SunneKatha

[![Frontend CI](https://github.com/anilkhatiwada/sunnekatha/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/anilkhatiwada/sunnekatha/actions/workflows/frontend-ci.yml)
[![Backend CI](https://github.com/anilkhatiwada/sunnekatha/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/anilkhatiwada/sunnekatha/actions/workflows/backend-ci.yml)

SunneKatha is an audio-first Nepali literature platform. The production system
uses a Next.js frontend, a Django REST Framework API, PostgreSQL, Redis/Celery,
private S3 storage, and CloudFront media delivery.

Production URLs:

- Application: <https://sunnekatha.com>
- API: <https://api.sunnekatha.com/api/v1>
- Admin: <https://api.sunnekatha.com/admin/>
- Media CDN: <https://media.sunnekatha.com>

## Architecture

- Next.js App Router and strict TypeScript provide the responsive web app and
  persistent native-audio player.
- TanStack Query owns API state; Zustand owns immediate playback and client
  state. All network access is isolated in `src/services/`.
- Django REST Framework provides JWT authentication, catalog, playlists,
  library, progress, queues, creator uploads, editorial administration, and
  secure stream handshakes.
- PostgreSQL is the system of record. Redis supports caching, throttling, and
  Celery. Celery worker and Beat run processing and aggregate tasks.
- S3 buckets remain private. Covers and free streams are delivered through
  CloudFront; restricted media uses short-lived signed URLs. Django never
  proxies audio bytes.

See [the frontend integration status](docs/frontend-integration-status.md),
[backend guide](backend/README.md), and
[production deployment guide](backend/docs/production-deployment.md).

## Requirements

- Node.js 22 LTS (Node 20.19+ is also supported; do not use odd-numbered Node)
- npm 10+
- Python 3.12+
- PostgreSQL 16+ with `pg_trgm` and `unaccent`
- Redis 7+
- FFmpeg and ffprobe for audio processing

## Frontend setup

```bash
npm ci
cp .env.example .env.local
npm run dev
```

The example environment uses mock content for safe UI development. To connect a
local frontend to Django, set:

```dotenv
NEXT_PUBLIC_API_MODE=remote
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_API_TIMEOUT_MS=15000
NEXT_PUBLIC_APP_ENV=local
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
```

Production is built with the checked-in browser-safe `.env.production`, which
uses the HTTPS API. `NEXT_PUBLIC_*` values are public by design and must never
contain credentials, private keys, refresh tokens, or service secrets.

## Backend setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements/local.txt
cp .env.example .env
python manage.py migrate
python manage.py setup_staff_roles
python manage.py runserver
```

Configure PostgreSQL and Redis in `backend/.env`. Local filesystem storage is
available for development; production settings require S3 and CloudFront
configuration and fail fast when required secrets are absent.

Run asynchronous workers in separate terminals:

```bash
cd backend
.venv/bin/celery -A config worker --loglevel=INFO
.venv/bin/celery -A config beat --loglevel=INFO
```

FFmpeg must be installed and visible on `PATH` to process uploaded masters.

## Environment documentation

- Frontend variables: [.env.example](.env.example)
- Backend variables: [backend/.env.example](backend/.env.example)
- AWS/S3/CloudFront and IAM: [backend README](backend/README.md)
- Deployment, backups, and rollback:
  [production deployment guide](backend/docs/production-deployment.md)

Production secrets belong in the host secret environment, never in Git.
Rotate Django, database, AWS, CloudFront, and OAuth secrets using the procedures
in the deployment guide.

## Validation

Frontend:

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm audit --omit=dev
```

Backend:

```bash
cd backend
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/pytest --cov=apps --cov=config --cov-fail-under=80
.venv/bin/python manage.py spectacular \
  --file /tmp/openapi-schema.yml --validate --fail-on-warn
```

GitHub Actions also applies migrations against PostgreSQL and runs with Redis.
Frontend CI gates lint, types, tests, the production build, and production npm
advisories.

## Demo data

`python manage.py seed_demo_data` is development-only and refuses to run with
`DEBUG=False`. Development credentials are documented in the backend README and
must never be copied to production. Production databases should be populated
only through approved editorial workflows or controlled metadata imports.

## Frontend integration

The production frontend uses `NEXT_PUBLIC_API_MODE=remote`; protected requests
use JWT access/refresh rotation and do not fall back to mock data. Playback first
fetches metadata, then requests `/tracks/{slug}/stream/?quality=auto` immediately
before play and uses the returned CloudFront URL.

Mock fixtures remain intentionally available only for local UI development.
Remote-mode gaps still tracked for product completion are listed in
[the integration status](docs/frontend-integration-status.md).

## Known limitations

- Payment-provider checkout is not implemented; premium access is managed by
  staff subscriptions and entitlements.
- Email and push delivery are not implemented; notifications are in-app only.
- Offline audio downloads and cross-device playback handoff are not implemented.
- Download in the full player is a visible placeholder and should not be
  presented as available in release messaging.
- Dedicated author/narrator playlist recommendations and personal listening
  statistics are not exposed by the API.
- JWTs are stored in browser local storage. This is compatible with the current
  JSON-token API but increases XSS impact; an HttpOnly refresh-cookie design is
  the recommended future hardening.
- Production operations currently depend on a single Lightsail instance and
  locally hosted PostgreSQL/Redis. Verify backups, restore, disk alarms, and
  rollback before each release.

## Release and deployment

Do not deploy directly from an unvalidated working tree. Merge through CI, build
an immutable release, run migrations once, collect Django static files, restart
Gunicorn/Celery/frontend services, and verify health, readiness, login, upload,
CloudFront cover delivery, free audio byte ranges, and signed premium playback.

Build or stage the Next.js standalone release for the production Linux target.
Before activating it, verify that `node_modules/@img/sharp-linux-x64` and
`node_modules/@img/sharp-libvips-linux-x64` match the installed `sharp` version.
A release assembled on macOS can otherwise omit these optional Linux packages,
causing `/_next/image` to fail at runtime. Smoke-test both an optimized cover URL
and the static social image at `/brand/sunnekatha-og.jpg` before switching the
production symlink.

The current release audit is documented in
[docs/first-public-release-audit.md](docs/first-public-release-audit.md).
