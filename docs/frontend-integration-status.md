# SunneKatha Frontend Integration Status

**Last updated:** 2026-07-30
**Frontend:** Next.js application at the repository root
**Backend:** Django REST Framework application in `backend/`
**API prefix:** `/api/v1`

This is the living implementation checklist for connecting the SunneKatha
frontend to the Django API. Update it whenever an integration phase is completed,
blocked, or materially changed.

## Status legend

- `[x]` Completed and covered by local validation
- `[ ]` Not started or incomplete
- **Blocked** Requires deployment or configuration work outside the frontend
- **Limited** Works with a documented compatibility limitation

## Current summary

| Area | Status | Notes |
| --- | --- | --- |
| API contract discovery | Completed | Frontend and backend routes, payloads, pagination, media flow, and authentication behavior were inspected |
| Environment and API client | Completed | Supports explicit `mock` and `remote` modes |
| Homepage | Completed locally | Uses the aggregate `/home/` response and preserves backend section order |
| Public catalog | Completed locally | Explore, taxonomy, tracks, playlists, authors, and narrators use remote services |
| Audio stream authorization | Completed locally | Stream URL is requested only after playback intent |
| Frontend deployment | Deployed to production domain | Commit `c9678e7` runs on the existing Lightsail instance |
| Live API verification | Verified | HTTPS, API routing, CORS, redirects, health, homepage, and Admin routing pass |
| Search | Completed locally | Grouped, track-only, autocomplete, trending, and pagination use Django in remote mode |
| Authentication and profile | In progress | Google Sign-In and JWT establishment are implemented locally; session-aware profile/logout remain |
| Library and relationships | Pending | Favorites, saved playlists, and follows remain local |
| Listening state | Pending | Progress, history, and playback sessions remain local |
| Queue synchronization | Pending | Player queue remains browser-local |
| User playlist management | Pending | Public detail is connected; authenticated mutations are not |
| Creator and uploads | Pending | No frontend creator/upload workflow is connected |

## Completed work

### 1. Discovery and API contract

- [x] Inspected frontend TypeScript models, mock services, query keys, routes,
  playlist and track structures, author and narrator structures, search
  structures, player progress, and library behavior.
- [x] Inspected Django routes, serializers, filters, permissions, pagination,
  media access, and OpenAPI output.
- [x] Recorded the detailed findings in
  `docs/frontend-backend-integration-analysis.md`.
- [x] Confirmed the API base path is `/api/v1`.
- [x] Confirmed the backend uses page-number pagination with `results`, `count`,
  `next`, and `previous`.

### 2. Frontend API foundation

- [x] Added validated public environment configuration.
- [x] Added explicit `mock` and `remote` API modes.
- [x] Required an API base URL when remote mode is enabled.
- [x] Required HTTPS for remote production configuration.
- [x] Centralized network requests in `src/services/api-client.ts`.
- [x] Added request timeouts and abort handling.
- [x] Added normalized API errors with status, code, field errors, and retry
  metadata.
- [x] Added bearer-token support and one controlled refresh/retry attempt.
- [x] Prevented concurrent requests from causing duplicate token refreshes.
- [x] Added serializable backend-facing TypeScript contracts.
- [x] Added backend-to-frontend mapping functions and safe fallback artwork.
- [x] Preserved the existing frontend domain names and UI component contracts.
- [x] Kept mock mode available for deterministic local development.

### 3. Aggregated homepage

- [x] Replaced multiple remote homepage requests with `GET /home/`.
- [x] Retained the original mock composition when API mode is `mock`.
- [x] Added runtime validation for the aggregate response.
- [x] Supported track, playlist, album, author, narrator, mood, genre, and
  continue-listening sections.
- [x] Preserved section identifiers, display titles, and backend ordering.
- [x] Hid empty or unsupported sections safely.
- [x] Supported anonymous responses and optional personalized sections.
- [x] Added an album card for homepage album content.
- [x] Added loading, error, retry, and empty states.

### 4. Public catalog

- [x] Connected Explore tracks to `GET /explore/tracks/`.
- [x] Connected content type, genre, and mood filters.
- [x] Connected genres to `GET /genres/`.
- [x] Connected moods to `GET /moods/`.
- [x] Connected featured playlists to `GET /playlists/featured/`.
- [x] Connected playlist detail to `GET /playlists/{slug}/`.
- [x] Connected track detail to `GET /tracks/{slug}/`.
- [x] Connected related tracks to `GET /tracks/{slug}/related/`.
- [x] Connected author detail to `GET /authors/{slug}/`.
- [x] Connected author tracks to `GET /tracks/author/{slug}/`.
- [x] Connected narrator detail to `GET /narrators/{slug}/`.
- [x] Connected narrator tracks to `GET /tracks/narrator/{slug}/`.
- [x] Connected featured author and narrator lists.
- [x] Unwrapped DRF pagination while preserving response ordering.
- [x] Converted detail `404` responses into the frontend's existing not-found
  states.

### 5. Media and playback boundary

- [x] Added `GET /tracks/{slug}/stream/?quality=auto`.
- [x] Kept private S3 keys and raw storage paths outside frontend models.
- [x] Request media authorization only after a user presses play.
- [x] Map an authorized stream response into a playable frontend track.
- [x] Preserve direct mock audio playback in mock mode.
- [x] Display a player error when stream authorization fails.

## Production deployment

The frontend is available at `https://sunnekatha.com`. Nginx routes
`api.sunnekatha.com` to Django and the apex domain to Next.js. `www` redirects
to the apex domain.

- Frontend URL: `https://sunnekatha.com`
- API URL: `https://api.sunnekatha.com/api/v1`
- Admin URL: `https://api.sunnekatha.com/admin/`
- Commit/release: `c9678e7-production`
- Frontend runtime: Node.js 22.23.1 and Next.js 16.2.10
- Frontend upstream: `127.0.0.1:3000`
- Django upstream: `127.0.0.1:8000`
- TLS: Let's Encrypt ECDSA certificate for the apex, `www`, and `api`
- Certificate expiry: 2026-10-28
- Fixed monthly cost added by HTTPS: `$0`

Production environment:

```text
NEXT_PUBLIC_API_MODE=remote
NEXT_PUBLIC_API_BASE_URL=https://api.sunnekatha.com/api/v1
NEXT_PUBLIC_APP_ENV=production
```

Django allows only the production hosts and explicitly trusts the production
HTTPS frontend/API origins for CORS and CSRF. SSL redirects and secure cookies
are enabled.

Verified after deployment:

- [x] Frontend root returns HTTPS 200.
- [x] HTTP redirects to HTTPS.
- [x] `www` redirects to the apex domain while preserving the request path.
- [x] Django health endpoint returns HTTPS 200.
- [x] Django Admin redirects to its login page.
- [x] Aggregated homepage API returns HTTPS 200 and valid JSON.
- [x] CORS returns the requested production frontend origin.
- [x] Frontend, Gunicorn, Celery worker, Celery Beat, and Nginx services are
  active.
- [x] Nginx configuration validation passes.
- [x] The production Next.js build uses the HTTPS API base URL.

Cloudflare records were kept DNS-only during certificate issuance and origin
verification. They may be proxied after setting Cloudflare SSL/TLS mode to
**Full (strict)**.

HSTS remains intentionally disabled until every intended subdomain, including
`media.sunnekatha.com`, is HTTPS-ready. The production settings include
`includeSubDomains` and preload behavior, so enabling HSTS prematurely would be
difficult to reverse.

## Blocked infrastructure

The private media CloudFront distribution is not yet created. AWS rejected the
creation request because the account must be verified before it can add new
CloudFront resources. No distribution charges are being incurred.

Already prepared:

- ACM certificate for `media.sunnekatha.com`
- CloudFront Origin Access Control
- CloudFront public key and trusted key group
- Published `SunneKathaMediaPathRewrite` CloudFront Function
- Version-controlled distribution configuration

Remaining actions:

- [ ] Complete AWS account verification for new CloudFront distributions.
- [ ] Create the previously approved distribution.
- [ ] Add the generated CloudFront hostname as the DNS-only
  `media.sunnekatha.com` CNAME.
- [ ] Apply the least-privilege S3 bucket policy for the distribution.
- [ ] Install the CloudFront signing key in the backend secret environment.
- [ ] Verify free, premium, unauthorized, and expired media access.
- [ ] Enable HSTS only after all required subdomains are confirmed HTTPS-ready.

## Known limitations

### Remote playlist queue

**Limited:** A remote playlist play action resolves and starts the selected
track. It does not pre-sign every track in the playlist.

This is intentional because premium CloudFront URLs are short-lived and bulk
authorization would create URLs that may expire before playback reaches them.
The queue phase should store catalog tracks and lazily authorize each track when
it becomes current.

### Author and narrator collections

**Limited:** The backend has direct author-track and narrator-track endpoints,
but no dedicated public endpoints for:

- playlists containing an author's work;
- playlists containing a narrator's tracks;
- related authors.

These optional UI sections remain empty in remote mode instead of downloading
large playlist or author collections and filtering them in the browser.

### Featured versus analytically popular people

Explore currently uses featured author and narrator endpoints as the compact
public source. If editorial “featured” and analytics-derived “popular” must be
distinct, the frontend should consume the aggregate Explore response or the
backend should expose dedicated popular endpoints.

### Remote data availability

The deployed homepage endpoint currently returns the expected section
identifiers, but its editorial sections may be empty until published demo or
production content is assigned through Django Admin.

## Pending phases

### Phase 5 — Search

- [x] Connect grouped search to `GET /search/`.
- [x] Connect track-only search to `GET /search/tracks/`.
- [x] Connect autocomplete to `GET /search/autocomplete/`.
- [x] Connect trending terms to `GET /search/trending/`.
- [x] Preserve Nepali Unicode and Romanized search behavior.
- [x] Add debounce, request cancellation, track pagination, empty, and error
  behavior.
- [x] Route compact search tracks through lazy stream authorization rather than
  treating catalog metadata as a playable URL.
- [x] Preserve deterministic mock search for local development.

### Phase 6 — Authentication and account

- [x] Add Google Identity Services sign-in page and button.
- [x] Verify Google ID credentials in Django and issue the existing JWT pair.
- [x] Store Google `sub` in a dedicated social identity model.
- [x] Prevent unsafe automatic linking of non-authoritative existing emails.
- [x] Preserve email/password authentication.
- [ ] Add registration and login forms.
- [ ] Connect login, registration, refresh, logout, and current-user endpoints.
- [ ] Complete secure token lifecycle behavior.
- [ ] Gate authenticated queries until a session is known.
- [ ] Connect profile and preference updates.
- [ ] Connect password change.
- [ ] Ensure logged-out and expired-session behavior is consistent.

### Phase 7 — Library relationships

- [ ] Replace local favorites with backend favorite list and mutations.
- [ ] Replace local saved playlists with backend save list and mutations.
- [ ] Replace local followed authors with backend follow list and mutations.
- [ ] Replace local followed narrators with backend follow list and mutations.
- [ ] Preserve idempotent mutations.
- [ ] Add relationship flags to relevant cards and details.
- [ ] Add optimistic updates with rollback on failure.

### Phase 8 — Listening progress and history

- [ ] Connect per-track progress reads and updates.
- [ ] Send progress every 15–30 seconds, on pause, on track change, and before
  leaving where possible.
- [ ] Connect continue listening.
- [ ] Connect completed and remove-from-continue-listening actions.
- [ ] Connect playback-session start, update, and end.
- [ ] Connect recently played and listening history.
- [ ] Avoid sending per-second events.

### Phase 9 — Queue synchronization

- [ ] Add server queue contracts and TanStack Query keys.
- [ ] Restore the queue after authentication.
- [ ] Keep the active browser player as the immediate source of truth.
- [ ] Synchronize replace, add, next, remove, reorder, clear, position, shuffle,
  and repeat operations.
- [ ] Lazily authorize a queued track when it becomes current.
- [ ] Handle expired signed URLs by requesting a fresh URL.
- [ ] Define conflict behavior for cross-device changes.

### Phase 10 — User playlists

- [ ] Connect create, update, and delete.
- [ ] Connect add, remove, and reorder track actions.
- [ ] Connect visibility changes and duplication.
- [ ] Enforce private, unlisted, and public visibility in the UI.
- [ ] Add ownership and permission error states.

### Phase 11 — Remaining catalog routes

- [ ] Replace the `/playlists` placeholder with a paginated public list.
- [ ] Add literary-work detail/list UI if it remains in product scope.
- [ ] Add album detail/list UI if it remains in product scope.
- [ ] Add genre and mood detail routes if they remain in product scope.
- [ ] Add pagination controls or infinite loading for large lists.
- [ ] Add language, author, narrator, premium, explicit, and ordering filters
  where appropriate.

### Phase 12 — Creator uploads

- [ ] Add creator authorization and profile UI.
- [ ] Connect upload-session request, direct S3 upload, confirmation,
  cancellation, and status.
- [ ] Connect draft metadata and processing status.
- [ ] Connect review submission.
- [ ] Never expose credentials, private S3 URLs, or server-controlled object
  keys as editable input.

### Phase 13 — Final integration and production verification

- [ ] Remove mock dependencies only after every consumer has migrated.
- [ ] Decide whether mock mode remains as a development/demo feature.
- [ ] Remove copyrighted or obsolete demo media before production.
- [ ] Run end-to-end tests against a staging API.
- [ ] Verify anonymous, authenticated, premium, expired, and staff scenarios.
- [ ] Verify responsive behavior and accessibility.
- [ ] Verify token refresh, throttling, and standardized errors.
- [ ] Verify CloudFront free and signed premium streams.
- [ ] Run lint, type checks, tests, and a production build.
- [ ] Produce the final frontend-backend compatibility report.

## Latest validation evidence

The following checks passed after the Search integration:

```text
npm run typecheck
npm run lint
npm test -- --run
npm run build
git diff --check
```

Results:

- TypeScript: passed
- ESLint: passed with no warnings
- Tests: 48 passed across 15 files
- Next.js production build: passed
- Diff whitespace validation: passed

These are local checks. They do not replace browser-level staging verification,
which remains blocked by the deployed CORS configuration.

## Recommended next action

Begin Phase 6, Authentication and account. The API client already has
single-flight JWT refresh and per-tab token storage. Google Sign-In now
establishes that JWT session; the next step is current-user bootstrap, logout,
session-aware navigation, profile/preferences updates, password behavior for
social-only accounts, and protected-query gating before integrating personalized
library and listening state.
