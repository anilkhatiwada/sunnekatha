# SunneKatha frontend integration status

**Last updated:** 2026-08-10

**Frontend:** `https://sunnekatha.com`

**API:** `https://api.sunnekatha.com/api/v1`

## Current status

| Area | Status |
| --- | --- |
| API client, errors, pagination, 404 mapping | Complete |
| Homepage and public catalog | Complete |
| Tracks, works, albums, authors, narrators, taxonomy | Complete |
| Secure CloudFront stream handshake | Complete |
| Google and email authentication | Complete |
| Profile, preferences, password, logout | Complete |
| Favorites, saved playlists, follows | Complete |
| Continue listening, progress, history | Complete |
| Playback sessions | Complete |
| Queue synchronization and restoration | Complete |
| Public and user playlist management | Complete |
| Grouped, paginated, autocomplete search | Complete |
| Notifications | Complete |
| Creator center and direct S3 uploads | Complete |
| Private S3 and CloudFront media delivery | Complete |
| Responsive and interaction review | Complete locally |
| Production deployment of this change | Deployed |

## Production release

- Application commit: `bef742f4fe78aef2dd0d5b433068a6c71498820f`
- Frontend release: `/srv/sunnekatha/frontend/releases/bef742f-production`
- Backend release: `/srv/sunnekatha/releases/bef742f-backend-integration`
- Deployed: 2026-07-30
- New AWS resources: none
- Added monthly cost: `$0`

Post-deployment verification:

- `https://sunnekatha.com/`: HTTP 200
- `/login`, `/playlists`, and `/notifications`: HTTP 200
- API health: HTTP 200
- Anonymous `playlists/?mine=true`: HTTP 401 as required
- Work track filter: HTTP 200
- Frontend, Gunicorn, Celery worker, and Celery Beat: active

## CloudFront media delivery

- Distribution: `SunneKathaMediaDistribution`
- Distribution ID: `E1F8UZR7Q8N16Y`
- CloudFront hostname: `d3dazzi8rnwbjc.cloudfront.net`
- Custom hostname: `media.sunnekatha.com`
- S3 origin: `sunnekatha-prod-media-533463644243-ap-south-1`
- OAC: `SunneKathaMediaOAC` (`E2NV3UGUN46AWN`)
- Trusted key group: `SunneKathaMediaSigning`
- Active public signing key: `SunneKathaMediaPublicKeyV2` (`K2H067RBECFGR8`)
- Price class: `PriceClass_100`

The bucket remains private with all S3 public-access blocks enabled. Its policy
allows `s3:GetObject` only when requested by the exact CloudFront distribution
ARN. `/covers/*` and `/free/*` are public viewer paths. `/premium/*`,
`/restricted/*`, and the default behavior require the trusted key group.

Cloudflare uses this DNS-only CNAME:

```text
Type: CNAME
Name: media
Target: d3dazzi8rnwbjc.cloudfront.net
Proxy status: DNS only
TTL: Auto
```

Production verification completed on 2026-08-10:

- homepage API cover URLs use `media.sunnekatha.com` instead of S3;
- a public cover returns HTTP 200 through CloudFront;
- direct S3 access returns HTTP 403;
- free audio supports HTTP 206 byte-range playback without a signature;
- premium audio supports HTTP 206 only with a 300-second signed URL;
- unsigned premium and restricted paths return HTTP 403.

The production `npm ci` audit reported 11 high-severity dependency findings.
No automatic force-upgrade was applied during deployment because it could make
breaking dependency changes. Review with `npm audit` in a dedicated dependency
hardening change.

## Added frontend routes

- `/work/[slug]`
- `/album/[slug]`
- `/genre/[slug]`
- `/mood/[slug]`
- `/playlists`
- `/notifications`
- `/history`
- `/creator`
- `/creator/uploads`

Existing protected routes hide account navigation before login and redirect
unauthenticated direct visits to `/login`.

## Backend compatibility additions

- Authenticated `GET /playlists/?mine=true`
- Track list filters `work={slug}` and `album={slug}`
- `isOwnedByCurrentUser` on playlist responses

No migrations were required.

## Validation results

Most recent completed validation:

- TypeScript: passed
- ESLint: passed with zero warnings
- Vitest: **69 passed**
- Next.js production build: passed
- Django checks: passed
- Django migration drift check: passed
- Full Django pytest suite: **608 passed**
- `git diff --check`: passed

Run the full commands before deployment:

```bash
npm run typecheck
npm run lint
npm test
npm run build
cd backend
.venv/bin/python manage.py check --settings=config.settings.test
.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.test
.venv/bin/pytest
```

## Deliberately pending product work

- Offline downloads
- Payment-provider checkout
- External push/email delivery
- Self-service creation of a draft track from a confirmed upload
- Privacy-scoped personal listening-statistics API
- Dedicated author/narrator playlist recommendation APIs

See `docs/frontend-backend-integration-report.md` for the contract audit,
security notes, and compatibility risks.
