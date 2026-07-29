# SunneKatha Django API

[![Backend CI](https://github.com/anilkhatiwada/sunnekathaapp/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/anilkhatiwada/sunnekathaapp/actions/workflows/backend-ci.yml)

Production-oriented Django REST Framework API for SunneKatha. It implements
catalog discovery, creators, playlists, listener libraries, progress and
history, synchronized queues, search, subscriptions and entitlements, secure
direct uploads, CloudFront media authorization, editorial homepage management,
notifications, and privacy-preserving analytics.

## Architecture

The repository uses one immutable backend image with separate process roles:

```text
Next.js / mobile clients
          |
    HTTPS load balancer
          |
   Gunicorn + Django REST
      |       |       |
 PostgreSQL  Redis   private S3
              |          |
       cache / broker  CloudFront
              |
      Celery worker + Beat
```

- Django REST Framework owns synchronous API, permission, and validation
  boundaries.
- PostgreSQL is the durable source of truth and supplies full-text/trigram
  search.
- Redis is shared by Django caching, DRF throttling, and Celery broker/result
  storage. Use separate logical databases or clusters according to operational
  scale.
- S3 stores private originals, processed streams, covers, and temporary direct
  uploads. CloudFront serves media; Django never proxies audio bytes.
- Celery Beat schedules daily analytics aggregation. Audio transcoding is not
  implemented yet; see **Known limitations**.
- Public serializers use compact list representations and detailed object
  representations. API JSON uses frontend-compatible camelCase names.

## Requirements

- Python 3.12+
- PostgreSQL 16+ (PostgreSQL 17 is used by Compose)
- Redis 7+
- FFmpeg for media inspection/transcoding tooling and future audio processing
- Docker with Compose, optional

## Installation

Run from the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/local.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The default `DATABASE_URL` expects a local database named `sunnekatha` with a
`sunnekatha` user and password on port 5432. Change `backend/.env` for your
environment. Never commit `.env`.

### Database setup

Create a local PostgreSQL role and database:

```sql
CREATE ROLE sunnekatha WITH LOGIN PASSWORD 'choose-a-local-password';
CREATE DATABASE sunnekatha OWNER sunnekatha;
```

Set the matching `DATABASE_URL`, then apply and verify migrations:

```bash
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
```

Production migrations run once as a release task, never concurrently in every
web replica.

### Redis setup

Start Redis locally with your package manager or:

```bash
docker run --name sunnekatha-redis --publish 6379:6379 redis:7.4-alpine
```

Use distinct Redis database URLs for cache, Celery broker, and Celery results.
Production defaults require `rediss://`; set `ALLOW_INSECURE_REDIS=true` only
for a network-isolated deployment where TLS is terminated elsewhere.

### Celery setup

Run one or more workers and exactly one Beat scheduler:

```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

The configured periodic job aggregates the previous day's analytics at 02:15
UTC. Workers use late acknowledgement, retry-on-worker-loss, bounded timeouts,
and a prefetch multiplier of one in production.

### FFmpeg setup

The production image installs FFmpeg. For local development:

```bash
# macOS
brew install ffmpeg

# Debian/Ubuntu
sudo apt-get update
sudo apt-get install ffmpeg

ffmpeg -version
ffprobe -version
```

FFmpeg is present for operational media tooling and the future processing
pipeline. Confirming an upload currently validates its signature but does not
transcode or promote it automatically.

The API is available at:

- Health/liveness: <http://localhost:8000/api/v1/health/>
- Dependency readiness: <http://localhost:8000/api/v1/readiness/>
- Application version: <http://localhost:8000/api/v1/version/>
- OpenAPI schema: <http://localhost:8000/api/schema/>
- Swagger UI: <http://localhost:8000/api/docs/>
- ReDoc: <http://localhost:8000/api/redoc/>
- JWT login: <http://localhost:8000/api/v1/auth/token/>
- JWT refresh: <http://localhost:8000/api/v1/auth/token/refresh/>

Account endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register/` | Register and receive an access/refresh pair |
| `POST` | `/api/v1/auth/login/` | Email/password login alias |
| `POST` | `/api/v1/auth/token/` | Email/password login |
| `POST` | `/api/v1/auth/token/refresh/` | Rotate access and refresh tokens |
| `POST` | `/api/v1/auth/logout/` | Blacklist the submitted refresh token |
| `GET` | `/api/v1/auth/me/` | Return the current user |
| `PATCH` | `/api/v1/auth/profile/` | Update email, username, display name, or avatar |
| `PATCH` | `/api/v1/auth/preferences/` | Update listening preferences |
| `POST` | `/api/v1/auth/change-password/` | Change password and revoke refresh tokens |

Email is the primary login identifier. JSON uses frontend-compatible camelCase
names such as `displayName`, `preferredLanguage`, and
`defaultPlaybackSpeed`. Registration requires `username`, `email`,
`displayName`, `password`, and `passwordConfirm`.

Refresh rotation and blacklisting are enabled. Refresh tokens currently travel
in JSON to preserve the frontend contract. A same-origin HttpOnly cookie remains
the preferred future browser integration and requires a coordinated frontend
authentication change.

### Authors and narrators

Public creator endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/authors/` | Paginated author list |
| `GET` | `/api/v1/authors/featured/` | Paginated featured authors |
| `GET` | `/api/v1/authors/{slug}/` | Author detail |
| `GET` | `/api/v1/narrators/` | Paginated narrator list |
| `GET` | `/api/v1/narrators/featured/` | Paginated featured narrators |
| `GET` | `/api/v1/narrators/{slug}/` | Narrator detail |

Lists support `search`, `ordering`, `featured`, `verified`, `page`, and
`pageSize`. Author ordering fields are `name_ne`, `name_en`, `birth_date`,
`created_at`, and `updated_at`. Narrator ordering fields are `name_ne`,
`name_en`, `follower_count_cache`, `created_at`, and `updated_at`; prefix a
field with `-` for descending order.

Public JSON preserves frontend-oriented names: Nepali names and biographies are
`name` and `biography`, English variants use `nameEnglish` and
`biographyEnglish`, and narrator follower counts use `followerCount`.

### Catalog taxonomies

Public taxonomy endpoints:

| Method | Endpoint |
| --- | --- |
| `GET` | `/api/v1/genres/` |
| `GET` | `/api/v1/moods/` |
| `GET` | `/api/v1/languages/` |
| `GET` | `/api/v1/content-categories/` |

Taxonomies are intentionally unpaginated small collections, ordered by
`sortOrder`, and expose frontend-compatible `name` and `nameEnglish` fields.
Use `?active=true` or `?active=false` to filter status. Search and ordering are
also supported through `search` and `ordering`.

After migrations, seed the standard SunneKatha values with:

```bash
python manage.py seed_taxonomies
```

The command is transactional and idempotent. It creates or updates managed
fields for common genres, moods, languages, and content categories without
deleting administrator-created records.

### Literary works and albums

Public catalog endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/works/` | Paginated published literary works |
| `GET` | `/api/v1/works/featured/` | Published featured works |
| `GET` | `/api/v1/works/{slug}/` | Published work detail |
| `GET` | `/api/v1/albums/` | Paginated published albums |
| `GET` | `/api/v1/albums/featured/` | Published featured albums |
| `GET` | `/api/v1/albums/{slug}/` | Published album detail |

Work filters are `contentType`, `author`, `genre`, `mood`, `language`,
`featured`, and `published`. Album filters are `author`, `genre`, `mood`,
`featured`, and `published`; albums do not have content-type or language fields.
Author, genre, mood, and language values are stable slugs. Both lists support
`ordering`, `page`, `pageSize`, and title `search`.

PostgreSQL uses weighted full-text title search across Nepali and English
titles. The isolated SQLite test settings use a multi-term case-insensitive
fallback. Public querysets always apply publication visibility first; filters
cannot reveal drafts, and scheduled works remain hidden until `publishedAt`.

### Audio tracks and media access

Public track endpoints:

| Method | Endpoint |
| --- | --- |
| `GET` | `/api/v1/tracks/` |
| `GET` | `/api/v1/tracks/featured/` |
| `GET` | `/api/v1/tracks/trending/` |
| `GET` | `/api/v1/tracks/recent/` |
| `GET` | `/api/v1/tracks/content-type/{contentType}/` |
| `GET` | `/api/v1/tracks/author/{authorSlug}/` |
| `GET` | `/api/v1/tracks/narrator/{narratorSlug}/` |
| `GET` | `/api/v1/tracks/genre/{genreSlug}/` |
| `GET` | `/api/v1/tracks/mood/{moodSlug}/` |
| `GET` | `/api/v1/tracks/{slug}/related/` |
| `GET` | `/api/v1/tracks/{slug}/` |
| `GET` | `/api/v1/tracks/{slug}/player/` |

Track lists use a compact serializer, detail uses the detailed serializer, and
the player endpoint uses the player serializer. General list filters include
`contentType`, `author`, `narrator`, `genre`, `mood`, `language`, `featured`,
`premium`, and `explicit`; lists also support `search`, `ordering`, `page`, and
`pageSize`.

Only ready, published tracks whose `publishedAt` has been reached are visible.
The AudioTrack table keeps a non-editable content-type cache because PostgreSQL
cannot index a joined LiteraryWork field; saving a track synchronizes the cache
from its work.

Raw audio master and stream storage fields are never serialized. The player
serializer delegates exclusively to `apps.media_access` for access URLs, so the
configured private storage backend remains responsible for expiring/signing
URLs. The dedicated stream endpoint uses CloudFront and a time-bounded premium
entitlement; it never proxies media bytes through Django.

### S3 media storage

Local and test settings store media below `backend/media/`. Production requires
`USE_S3_STORAGE=true`, a private audio bucket, and a cover bucket. Storage is
split into lifecycle-ready prefixes:

| Storage alias | Bucket | Object prefix | Access |
| --- | --- | --- | --- |
| `original_audio` | audio | `originals/audio/` | Private, signed URLs |
| `processed_audio` | audio | `processed/audio/` | Private, signed URLs |
| `default` (covers) | covers | `covers/` | Private signed URL, or CloudFront |
| `temporary_uploads` | audio | `temporary/uploads/` | Private, signed URLs |

Object names discard the client filename and use a UUID under the model and
record UUID. Extensions are normalized and allow-listed. Image and audio
validators enforce extensions, declared MIME types, and configurable maximum
sizes before storage. Processing-time signature inspection remains part of the
future media-processing pipeline; it is not implemented here.

The lifecycle prefix is part of each new object key rather than the storage
root. This lets legacy `images/...` and `audio/...` database names continue to
resolve while all new uploads use the paths in the table above. Existing
objects still need to be copied into the configured bucket during deployment;
database names do not contain bucket names or credentials.

Required non-secret environment variables:

```dotenv
USE_S3_STORAGE=true
AWS_S3_REGION_NAME=us-east-1
AWS_S3_AUDIO_BUCKET_NAME=sunnekatha-private-audio
AWS_S3_COVER_BUCKET_NAME=sunnekatha-private-covers
AWS_CLOUDFRONT_DOMAIN=media.example.com
AWS_QUERYSTRING_EXPIRE=900
CLOUDFRONT_MEDIA_DOMAIN=audio.example.com
CLOUDFRONT_KEY_PAIR_ID=KXXXXXXXXXXXXX
CLOUDFRONT_PRIVATE_KEY=
CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS=300
UPLOAD_SESSION_EXPIRY_SECONDS=900
```

Do not put AWS access keys in `.env`, source control, container images, or
Django settings. In AWS, attach the least-privilege policy to the ECS task,
EC2 instance, Lambda, or workload role. For local administrative access, use an
AWS profile or another boto3 credential-provider-chain source.

The CloudFront private key is also a secret. Inject it at runtime from the
deployment secret manager; use `\n` escapes if the provider supplies a
single-line value. Never commit the PEM file or bake it into an image.

An application-role policy needs only bucket listing for the managed prefixes
and object operations used by uploads, delivery, replacement, and cleanup:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListManagedPrefixes",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::sunnekatha-private-audio",
        "arn:aws:s3:::sunnekatha-private-covers"
      ],
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "originals/audio/*",
            "processed/audio/*",
            "temporary/uploads/*",
            "covers/*"
          ]
        }
      }
    },
    {
      "Sid": "ManageMediaObjects",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload"
      ],
      "Resource": [
        "arn:aws:s3:::sunnekatha-private-audio/originals/audio/*",
        "arn:aws:s3:::sunnekatha-private-audio/processed/audio/*",
        "arn:aws:s3:::sunnekatha-private-audio/temporary/uploads/*",
        "arn:aws:s3:::sunnekatha-private-covers/temporary/uploads/*",
        "arn:aws:s3:::sunnekatha-private-covers/covers/*"
      ]
    }
  ]
}
```

Keep S3 Block Public Access enabled on the audio bucket and do not grant
`s3:GetObject` to `Principal: "*"`. If covers use CloudFront, configure an
Origin Access Control and grant the CloudFront service principal read access
only to `covers/*`, restricted by the distribution `AWS:SourceArn`. The
application role still requires cover write/delete access.

Bucket CORS is needed only when a browser directly uses presigned upload or
download URLs. Restrict `AllowedOrigins` to deployed frontend origins; never
use `*` with credentials. A suitable starting point is:

```json
[
  {
    "AllowedOrigins": ["https://app.example.com"],
    "AllowedMethods": ["GET", "HEAD", "PUT", "POST"],
    "AllowedHeaders": [
      "content-type",
      "x-amz-date",
      "x-amz-security-token",
      "x-amz-content-sha256",
      "authorization"
    ],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Server-side Django uploads do not require bucket CORS. Narrow the methods to
`GET` and `HEAD` until direct uploads are introduced.

Recommended lifecycle rules are prefix-based: abort incomplete multipart
uploads after one day; expire `temporary/uploads/` objects after one to three
days; transition `originals/audio/` to an appropriate archival storage class
after the operational recovery window; and retain `processed/audio/` according
to the publication and regeneration policy. Enable bucket versioning before
automated expiration and define noncurrent-version retention explicitly.

#### Direct uploads

Active creators and staff can upload audio masters and catalog images without
proxying file bodies through Django:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/uploads/` | Create a session and receive a presigned POST |
| `GET` | `/api/v1/uploads/{id}/` | Check the owner-scoped session status |
| `POST` | `/api/v1/uploads/{id}/confirm/` | Verify the S3 object and confirm |
| `POST` | `/api/v1/uploads/{id}/cancel/` | Delete any temporary object and cancel |

The request body uses `uploadType`, `originalFilename`, `contentType`, and
`expectedSize`. Supported types are `audio_master`, `cover_image`,
`narrator_image`, and `author_image`. The client must submit the returned POST
URL and every returned form field unchanged, add the file body, then call the
confirmation endpoint. The policy fixes the object key, MIME type, AES-256
encryption field, and a narrow body-size range that allows multipart form
overhead. A confirmation succeeds only when `HeadObject` reports the exact
expected object size and MIME type.

The original filename is retained only for display/audit purposes. It is
stripped to a basename and never becomes an S3 key. Temporary keys have the
form `temporary/uploads/{kind}/{user UUID}/{session UUID}/{random UUID}.{ext}`.
Expired and abandoned objects should be removed by the bucket lifecycle rule;
no media processing or promotion is performed yet.

#### CloudFront audio delivery

`GET /api/v1/tracks/{slug}/stream/?quality=auto` authorizes playback and returns
the selected `low` or `high` quality, a CloudFront URL, nullable `expiresAt`,
compact track metadata, and authorization status. `auto` prefers high quality
and falls back to low. Django returns metadata only and never downloads,
buffers, redirects through, or proxies the audio bytes.

Published free tracks receive stable `/free/` URLs. Premium tracks receive
signed `/premium/` URLs; unpublished tracks available to staff or their linked
narrator/creator receive signed `/restricted/` URLs. Signed URLs expire after
five minutes by default, and production rejects values outside 30–900 seconds.
Anonymous users may stream free published tracks. Premium playback requires a
current subscription or track-specific entitlement; staff and the track's
linked narrator account are privileged operational paths.

Keep the S3 origin private with Origin Access Control. Configure CloudFront
cache behaviors so `/premium/*` and `/restricted/*` require a trusted key group,
while `/free/*` permits unsigned viewers. An origin-request CloudFront Function
or Lambda@Edge rule must strip only the first routing segment before requesting
the underlying private S3 key. Do not configure a catch-all public behavior
that can reach premium objects. Use separate distributions if routing-prefix
rewrites are not acceptable.

When a previously free track becomes premium or unpublished, invalidate its
old `/free/*` URL and rotate or move the processed object as part of the future
publication workflow. CloudFront access logs should be enabled without logging
viewer authorization headers or application JWTs.

### Subscriptions and entitlements

`apps.subscriptions` models access without integrating a payment provider:

- `SubscriptionPlan` declares free/premium streaming and download capabilities.
- `UserSubscription` records active, trial, expired, canceled, or
  `staff_granted` access windows.
- `ContentEntitlement` grants stream and/or download access to one track with
  optional expiration and revocation.

A user with no current grant is a free user. Current means the start time has
passed, the optional end time has not passed, the status is active, trial, or
staff-granted, and the plan remains enabled. Staff-granted status explicitly
enables premium streaming for test and support workflows. No prices, checkout
sessions, provider customer IDs, invoices, webhooks, or billing state exist.

Reusable policy helpers live in `apps.subscriptions.permissions`:
`can_access_premium`, `can_stream_track`, and `can_download_track`. Media
delivery uses these helpers as its entitlement source. Django Admin actions on
user subscriptions grant selected records as staff test access or revoke them;
both actions record the staff actor or cancellation timestamp as applicable.

### Creator workflow

Creator APIs are rooted at `/api/v1/creator/`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET`, `PATCH` | `profile/` | View or update the current creator profile |
| `GET` | `tracks/` | List contributed or narrated tracks |
| `GET` | `tracks/drafts/` | List owned unpublished tracks |
| `GET` | `uploads/` | List the creator's upload sessions |
| `GET` | `tracks/{slug}/processing/` | View processing and review state |
| `POST` | `tracks/{slug}/submit/` | Submit a ready draft for staff review |
| `PATCH` | `tracks/{slug}/metadata/` | Update owned draft metadata |
| `POST` | `tracks/{slug}/approve/` | Staff-only approval and publication |
| `GET` | `tracks/{slug}/analytics/` | View basic owned-track analytics |

`CreatorProfile` records narrator, editor, uploader, and rights-holder roles.
Actual track authority is explicit through `ContentContributor` or the linked
narrator account; setting a profile role alone does not grant access to every
track. Creators can edit only owned, unpublished draft/rejected records and
cannot submit publication fields. Only staff can approve and publish.

Copyright owner, status, and license-note updates additionally require a
rights-holder contribution (or staff access). Every effective rights change
writes an immutable `RightsLicenseAudit` entry containing actor, track,
timestamp, and before/after values. Processing state remains separate from
editorial review state.

## Docker setup

From the repository root:

```bash
cp backend/.env.example backend/.env
docker compose build
docker compose up
```

Compose starts PostgreSQL, waits for database readiness, applies migrations, and
starts Django at <http://localhost:8000>. Stop services with:

```bash
docker compose down
```

To also remove the development database volume, explicitly run:

```bash
docker compose down --volumes
```

The last command deletes local database data.

## Validation commands

From `backend/` with the local requirements installed:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
pytest
pytest --cov=apps --cov=config --cov-report=term-missing --cov-fail-under=80
ruff check .
ruff format --check .
python manage.py spectacular --file openapi-schema.yml --validate --fail-on-warn
```

Tests use `config.settings.test` and an isolated in-memory SQLite database. This
keeps unit and endpoint tests deterministic; normal local and production
settings remain PostgreSQL-only.

The backend GitHub Actions workflow runs for pull requests and pushes to
`main`. It uses `config.settings.ci` with PostgreSQL and Redis service
containers, verifies that migrations apply, enforces the 80% coverage floor,
and fails on OpenAPI validation warnings. Coverage XML and the generated schema
are retained as workflow artifacts for 14 days.

No Python type checker is currently configured. CI reports that step as
skipped; adding `mypy.ini` or a `[tool.mypy]` section enables the command once
`mypy` is included in the local requirements.

## Editorial admin

Open `/admin/` with a staff account. Core catalog, identity, upload, and
subscription records cannot be deleted through the admin; use publication,
revocation, or active-state controls instead.

Publication and featured-state changes are available as bulk actions. Track
publication only accepts approved, processed records. The separate approve and
publish action accepts submitted, ready tracks and records the reviewing staff
member. Retry processing only moves failed tracks back to pending; a worker must
perform the actual processing. Playlist items remain explicitly ordered, and
album tracks link to their full track edit pages.

Homepage composition can be managed under **Home sections**. Sections are ordered
by `sort_order`, can be scheduled with `starts_at` and `ends_at`, and contain
explicitly positioned items. Item targets must match the section type; hero
sections accept tracks, playlists, or albums. Active editorial sections replace
the default homepage curation, while authenticated continue-listening content
remains personalized and is never placed in the shared public cache.

## Redis cache

Local and production settings use Redis through `django-redis`; Docker Compose
provides a persistent Redis service. Set `REDIS_URL` for the deployment and set
`REDIS_RAISE_EXCEPTIONS=true` in production so cache outages are observable.
Automated tests use an isolated in-memory cache.

Public cache durations are configurable:

| Content | Setting | Default |
| --- | --- | ---: |
| Public homepage sections | `HOME_PUBLIC_CACHE_TIMEOUT` | 300 seconds |
| Featured playlists, authors, and narrators | `FEATURED_CACHE_TIMEOUT` | 300 seconds |
| Genre and mood lists | `TAXONOMY_CACHE_TIMEOUT` | 900 seconds |
| Public playlist details and track metadata | `PUBLIC_DETAIL_CACHE_TIMEOUT` | 300 seconds |
| Non-personal admin dashboard metrics and rankings | `ADMIN_DASHBOARD_CACHE_TIMEOUT` | 60 seconds |

Cache keys include a resource generation, normalized query parameters where
applicable, and the request host. Publication services explicitly invalidate
affected generations after bulk state transitions. Model signals cover direct
changes to public catalog records and playlist membership. Favorites, continue
listening, private or unlisted playlists, queues, and authentication responses
are never stored in the shared public cache.

## Security

Security-sensitive limits, the permission audit, and production deployment
requirements are documented in
[`docs/security-hardening.md`](docs/security-hardening.md). Configure explicit
HTTPS CORS/CSRF origins, deploy behind a proxy that replaces forwarding headers,
and provide all secrets through the runtime environment or a workload secret
manager.

## Analytics workers

Celery aggregates playback sessions into privacy-preserving daily platform,
track, author, narrator, and playlist tables. Aggregate rows contain counts and
durations only; they do not retain user or device identifiers. Celery Beat runs
the previous-day aggregation at 02:15 UTC.

Run workers locally:

```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

The staff-only endpoints are:

- `GET /api/v1/staff/analytics/summary/`
- `GET /api/v1/staff/analytics/daily/`
- `GET /api/v1/staff/analytics/popular/`

They accept bounded `dateFrom` and `dateTo` parameters; the popular endpoint also
accepts `limit`. Multi-day unique-listener values are explicitly identified as
the sum of daily unique listeners because no cross-day user identifiers are
retained. Playlist popularity represents listening to tracks contained in the
playlist, not guaranteed playback origin.

Production runtime configuration, AWS reference architecture, migrations,
health checks, backups, and rollback procedures are documented in
[`docs/production-deployment.md`](docs/production-deployment.md).

## Settings

- `config.settings.base`: shared apps, middleware, database, REST Framework,
  JWT, CORS, schema, and logging defaults
- `config.settings.local`: debug mode, browsable API, console email
- `config.settings.production`: fail-fast secrets/hosts and secure proxy,
  cookie, redirect, HSTS, static assets, PostgreSQL/Redis TLS, and logging
- `config.settings.build`: image-build-only static collection
- `config.settings.test`: isolated test database and fast password hashing

Environment variables are documented in `.env.example`. Lists are
comma-separated.

## Shared infrastructure

`apps.common` provides:

- `UUIDTimeStampedModel`, `SoftPublishableModel`, publication status, and
  publication queryset helpers; all are abstract and create no domain tables
- Unicode-safe, collision-aware slug generation suitable for Nepali text
- page-number and cursor pagination matching the frontend's `pageSize` naming
- standardized `{ detail, code, errors? }` responses and a global DRF exception
  handler
- reusable admin/read-only, owner/read-only, and self/admin permissions
- image/audio extension, MIME, size, and safe-path validators
- collision-resistant image and audio upload path helpers
- allow-listed ordering normalization
- selectable-field and immutable-field serializer mixins
- standard drf-spectacular error response declarations

`apps.accounts` provides the UUID-based custom user, email authentication,
profile and preference management, JWT lifecycle endpoints, active-user
permissions, and Django admin integration. Social login is intentionally not
implemented.

`apps.authors` and `apps.narrators` provide bilingual creator records, stable
Unicode slugs, public discovery APIs, indexed featured/verified paths, and admin
search/filter/image-preview tooling. Narrator queries select the optional linked
account in the same query to avoid N+1 serialization.

`apps.taxonomy` provides genres, moods, languages, and content categories using
a shared abstract UUID taxonomy model, public list APIs, admin management, and
the repeatable `seed_taxonomies` command.

`apps.catalog` provides LiteraryWork and Album records, taxonomy relationships,
publication-safe public discovery, PostgreSQL title search, optimized related
object loading, AudioTrack discovery/player representations, and catalog admin
management.

`apps.media_access` is the dedicated boundary that converts authorized private
stream objects into media access URLs. API serializers must never call storage
URLs directly for audio.

`apps.playlists` provides editorial, user, and automatic-placeholder playlists
with stable ordered membership. Public playlist listings contain only published
public records; published unlisted playlists resolve by direct URL, and private
or draft playlists resolve only for their owners. Authenticated operations use:

- `POST /api/v1/playlists/` to create
- `PATCH` or `DELETE /api/v1/playlists/{slug}/` to update or delete
- `POST /api/v1/playlists/{slug}/tracks/add/` with `trackId`
- `POST` or `DELETE /api/v1/playlists/{slug}/tracks/remove/` with `trackId`
- `POST` or `PATCH /api/v1/playlists/{slug}/tracks/reorder/` with all `trackIds`
- `PATCH /api/v1/playlists/{slug}/visibility/`
- `POST /api/v1/playlists/{slug}/duplicate/`

Only staff can create, feature, or publish editorial and automatic-placeholder
playlists. Staff API access does not override the privacy of another user's
private playlist.

`apps.library` stores authenticated user relationships for favorite tracks,
saved playlists, followed authors, and followed narrators. Collection routes are
`GET /api/v1/library/{tracks|playlists|authors|narrators}/`. Relationship routes
accept idempotent `POST` or `PUT` to add and `DELETE` to remove:

- `/api/v1/library/tracks/{trackId}/favorite/`
- `/api/v1/library/playlists/{playlistId}/save/`
- `/api/v1/library/authors/{authorId}/follow/`
- `/api/v1/library/narrators/{narratorId}/follow/`

Responses include the applicable `is_favorited`, `is_playlist_saved`,
`is_author_followed`, or `is_narrator_followed` flag. Library collections retain
catalog publication and playlist privacy rules.

Listening progress uses one upserted record per user and track:

- `GET`, `PUT`, `PATCH`, or `DELETE /api/v1/me/listening-progress/{trackId}/`
- `POST /api/v1/me/listening-progress/{trackId}/complete/`
- `DELETE /api/v1/me/listening-progress/{trackId}/remove/`
- `GET /api/v1/me/continue-listening/`

Updates accept `progressSeconds` and `durationSeconds`. Stored track duration is
authoritative when available. Timing drift up to five seconds is clamped to the
duration; larger overshoots and negative positions are rejected. Progress at 90
percent or above is completed and therefore omitted from continue-listening.

Playback analytics are stored separately from resume progress:

- `POST /api/v1/me/playback-sessions/` starts or reuses an active session
- `PATCH /api/v1/me/playback-sessions/{sessionId}/` records cumulative listened
  time and an optional meaningful transition
- `POST /api/v1/me/playback-sessions/{sessionId}/end/` ends and rolls up a
  session exactly once
- `GET /api/v1/me/recently-played/`
- `GET /api/v1/me/listening-history/`

Session updates use cumulative `listenedSeconds`, so retries do not inflate
totals. Playback events are limited to started, resumed, paused, seeked,
completed, stopped, and error transitions. An optional `clientEventId` provides
database-backed deduplication; equivalent transitions repeated within two
seconds are also suppressed. The frontend does not need to submit per-second
events.

Server-side queue state is a restoration snapshot; the frontend player remains
the immediate playback authority. Queue routes are:

- `GET`, `PUT`, or `DELETE /api/v1/me/queue/`
- `POST /api/v1/me/queue/items/`
- `POST /api/v1/me/queue/play-next/`
- `DELETE /api/v1/me/queue/items/{queueItemId}/`
- `PATCH /api/v1/me/queue/reorder/`
- `PATCH /api/v1/me/queue/position/`
- `PATCH /api/v1/me/queue/shuffle/`
- `PATCH /api/v1/me/queue/repeat/`

Replacement accepts ordered `trackIds`, `currentIndex`, and `positionSeconds`.
Reordering accepts every current `itemId` exactly once. Queue item identity is
separate from track identity, so the same track may intentionally occur more
than once. Replacement and reordering lock the user queue transactionally.

The aggregated homepage is available at `GET /api/v1/home/`. It returns a
compact hero plus bounded sections identified as `featured-playlists`,
`trending-tracks`, `recently-added`, `popular-authors`, `popular-narrators`,
`mood-collections`, and `featured-albums`. Authenticated responses prepend
`continue-listening`.

Only the request-independent public payload is cached. Personalized progress is
queried and composed after the cached value is copied, so it is never written
to the shared cache. `HOME_PUBLIC_CACHE_TIMEOUT` controls the public cache TTL
and defaults to 300 seconds. Mood collections currently use active mood
taxonomy summaries with playable-track counts because playlists do not yet have
a mood relationship.

Authenticated notification endpoints are:

- `GET /api/v1/notifications/` (optionally `?unread=true` or `?unread=false`)
- `GET /api/v1/notifications/unread-count/`
- `POST` or `PATCH /api/v1/notifications/{notificationId}/read/`
- `POST /api/v1/notifications/read-all/`

Notification records are created inside existing publication and playlist
update workflows. Upload processors should call
`notification_service.upload_processing_completed()` or
`notification_service.upload_processing_failed()` when processing reaches a
terminal state. Notifications are in-app records only; this foundation does
not send email or push messages.

Upload MIME values are advisory client metadata. Domain upload processing must
later inspect file signatures and media contents before publication. Slug fields
must still have database uniqueness constraints because application-side
generation alone cannot prevent concurrent-write races.

## Structure

```text
backend/
  apps/
    accounts/             Custom user and account/JWT API
    analytics/            Privacy-preserving daily aggregates
    authors/              Author records and public discovery API
    catalog/              Works, albums, tracks, and editorial services
    common/               Shared models, API utilities, and system endpoints
    creators/             Creator ownership and review workflow
    home/                 Editorial homepage composition
    library/              Relationships, progress, history, and queues
    media_access/         CloudFront stream authorization
    narrators/            Narrator records and public discovery API
    notifications/        In-app notification foundation
    playlists/            Ordered editorial and user playlist APIs
    search/               PostgreSQL full-text/trigram search
    subscriptions/        Plans, subscriptions, and entitlements
    taxonomy/             Catalog taxonomies and seed command
    uploads/              Direct-to-S3 upload sessions
  config/
    settings/             Base, local, production, and test settings
    urls.py               API, schema, docs, and admin routes
    asgi.py
    wsgi.py
  requirements/
    base.txt
    local.txt
    production.txt
  Dockerfile
  manage.py
```

New Django applications belong under `apps/`. Domain models must follow the
frontend API analysis in `../docs/frontend-api-analysis.md` and require their
own Architect → Engineer → Reviewer milestone.

## Development demo data

Create the connected, fictional Nepali demo catalog with:

```bash
python manage.py seed_demo_data
```

The command is idempotent and runs only when `DEBUG=True`. To rebuild records
owned by the command, use:

```bash
python manage.py seed_demo_data --clear-existing-data
```

The clear option deletes only fixed demo users, catalog slugs, playlists, and
homepage section identifiers created by this command. It preserves unrelated
development records. Demo tracks intentionally contain no audio files and no
copyrighted audio.

Development-only accounts all use the password `SunneKathaDemo!2026`:

| Account | Email | Purpose |
| --- | --- | --- |
| Listener | `listener@sunnekatha.local` | Favorites, follows, and progress |
| Premium | `premium@sunnekatha.local` | Active demo subscription |
| Creator | `creator@sunnekatha.local` | Approved narrator/uploader |
| Editor | `editor@sunnekatha.local` | Staff editorial workflows |

These credentials are public test fixtures. Never enable or reuse them in
staging or production.

## Environment variables

Copy `.env.example` for the complete, executable template. The most important
variables are:

| Area | Variables |
| --- | --- |
| Django | `DJANGO_SETTINGS_MODULE`, `APP_VERSION`, `DJANGO_SECRET_KEY`, `DEBUG`, `DJANGO_ALLOWED_HOSTS` |
| Browser security | `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `CSRF_TRUSTED_ORIGINS` |
| PostgreSQL | `DATABASE_URL`, `DATABASE_CONN_MAX_AGE`, `DATABASE_CONNECT_TIMEOUT_SECONDS`, `DATABASE_SSL_MODE` |
| Redis | `REDIS_URL`, `REDIS_RAISE_EXCEPTIONS`, `ALLOW_INSECURE_REDIS` |
| Celery | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, worker concurrency, prefetch, shutdown, time-limit, and visibility-timeout settings |
| JWT | `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS` |
| Throttling | `DRF_ANON_THROTTLE_RATE`, `DRF_USER_THROTTLE_RATE`, scoped login, registration, upload, stream rates, and `DRF_NUM_PROXIES` |
| Upload limits | `DATA_UPLOAD_MAX_MEMORY_SIZE`, `FILE_UPLOAD_MAX_MEMORY_SIZE`, `MAX_IMAGE_UPLOAD_BYTES`, `MAX_AUDIO_UPLOAD_BYTES`, `MAX_PERMISSION_DOCUMENT_BYTES` |
| S3 | `USE_S3_STORAGE`, region, private audio/cover bucket names, optional development endpoint |
| CloudFront | media domains, key-pair ID, private signing key, signed-URL lifetime |
| Web runtime | Gunicorn bind, workers, threads, timeouts, request recycling, and trusted forwarding IPs |
| Security/logging | SSL redirect, HSTS, proxy trust, JSON log format |

Production settings fail fast for weak/default secrets, wildcard hosts,
non-HTTPS origins, non-PostgreSQL databases, insecure Redis unless explicitly
allowed, missing private-media configuration, unsafe signed-URL lifetimes, and
invalid trusted-proxy counts. Secrets must come from a workload secret manager.
AWS access keys should not be application environment variables when an IAM
workload role is available.

## Testing

Run the same quality gates as CI:

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=apps --cov=config --cov-report=term-missing --cov-fail-under=80
python manage.py spectacular \
  --file openapi-schema.yml \
  --validate \
  --fail-on-warn
```

CI additionally runs migrations against PostgreSQL 17 and uses Redis. Local
unit tests use isolated SQLite and in-memory cache settings, so a green local
run does not replace PostgreSQL migration and query-plan validation.

## Frontend integration

The Next.js application is still mock-backed. The backend contract comparison,
method-by-method mappings, pagination adapters, authentication behavior, secure
player handshake, and known gaps are documented in
[`../docs/frontend-backend-integration-report.md`](../docs/frontend-backend-integration-report.md).

The essential playback rule is:

1. fetch track metadata;
2. request `/api/v1/tracks/{slug}/stream/?quality=auto` immediately before play;
3. set the audio element source to the returned CloudFront `url`;
4. refresh signed premium URLs after `expiresAt`.

Do not add raw S3 fields or a persistent premium `audioUrl` to catalog
responses.

## Production deployment

Build the immutable image, validate production configuration, run a one-off
migration task, and deploy separate web, worker, and singleton Beat roles:

```bash
docker build --pull --tag sunnekatha-api:${APP_VERSION} .
docker run --rm --env-file production.env \
  sunnekatha-api:${APP_VERSION} check
docker run --rm --env-file production.env \
  sunnekatha-api:${APP_VERSION} migrate
```

Static assets are collected during image build. Web containers do not migrate
or collect static files at startup. Use at least two web replicas, one or more
workers, and exactly one Beat replica. Full AWS architecture, proxy rules,
health checks, migration strategy, backups, rollback, and deployment checklists
are in [`docs/production-deployment.md`](docs/production-deployment.md).

## Known limitations

- Audio transcoding, waveform generation, loudness normalization, and promotion
  from confirmed temporary uploads are not implemented. The admin recovery
  action truthfully resets failed tracks to `pending`; it does not enqueue an
  unavailable processor. Publication remains blocked until a track is marked
  ready by an authorized operational workflow.
- Upload confirmation verifies extension/MIME agreement, exact stored object
  size, AES-256 metadata, and common file signatures. It is not a malware
  scanner or full media decoder.
- Payment-provider integration and social login are intentionally absent.
- Browser refresh tokens currently use the JSON contract. A same-origin
  HttpOnly-cookie design requires coordinated frontend changes.
- Stable free CloudFront URLs require an operational invalidation or object-move
  procedure when content becomes premium or unpublished.
- The frontend is not connected to the API and must implement the secure stream
  handshake plus compact/detail response adapters.
- Search indexes and production query budgets must be verified with
  representative PostgreSQL data; SQLite tests do not model PostgreSQL plans.
- Personal listener statistics are not exposed; existing analytics endpoints
  are staff-only and privacy-thresholded.
