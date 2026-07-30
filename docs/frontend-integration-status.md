# SunneKatha frontend integration status

**Last updated:** 2026-07-30

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
| Responsive and interaction review | Complete locally |
| Production deployment of this change | Pending user authorization/SSH access |

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
