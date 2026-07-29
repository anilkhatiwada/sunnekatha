# SunneKatha Frontend Integration Status

**Last updated:** 2026-07-29
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
| Frontend deployment | Deployed to staging IP | Commit `9536ce9` runs on the existing Lightsail instance |
| Live API verification | Partially verified | HTTP smoke tests pass; normal-browser data verification remains pending |
| Search | Pending | Still uses local mock search |
| Authentication and profile | Pending | JWT client foundation exists, but user-facing authentication is not connected |
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

## Blocked work

### Production domain and browser verification

The frontend is available from `http://13.205.30.123/`, with Nginx serving the
Next.js application and preserving Django under `/api/`, `/admin/`, `/static/`,
and `/media/`. The frontend and API are same-origin for this staging-IP build,
so CORS is not required for that temporary route.

Production domain verification remains incomplete. The final frontend will use
`https://sunnekatha.com`, while the API will use
`https://api.sunnekatha.com/api/v1`; those origins require restricted CORS and
CSRF configuration.

Required actions:

- [ ] Decide the exact local, staging, and production frontend origins.
- [ ] Add only those origins to the backend CORS allowlist.
- [ ] Add corresponding trusted HTTPS origins where Django CSRF protection
  applies.
- [ ] Avoid wildcard CORS or wildcard trusted origins in production.
- [ ] Restart or redeploy the backend after changing environment configuration.
- [ ] Verify homepage, Explore, detail pages, and stream authorization from the
  actual browser origin.
- [ ] Replace the temporary HTTP/IP API URL with an HTTPS API domain before
  production.

### Current deployment

- Commit: `9536ce9`
- Frontend service: `sunnekatha-frontend.service`
- Frontend runtime: Node.js 22.23.1 and Next.js 16.2.10
- Frontend upstream: `127.0.0.1:3000`
- Public staging URL: `http://13.205.30.123/`
- API staging URL: `http://13.205.30.123/api/v1`
- Fixed monthly cost added: `$0`

Verified after deployment:

- [x] Frontend root returns HTTP 200.
- [x] Web app manifest returns HTTP 200.
- [x] Django health endpoint returns HTTP 200.
- [x] Django Admin remains reachable and redirects to its login page.
- [x] Aggregated homepage API returns HTTP 200 and valid JSON.
- [x] Frontend, Gunicorn, Celery worker, Celery Beat, and Nginx services are
  active.
- [x] Nginx configuration validation passes.
- [x] The rendered application shell, navigation, and player are present.
- [ ] Complete homepage data verification in a normal browser. The automated
  in-app browser used during deployment does not expose `window.fetch`, so it
  cannot validate client-side API requests.

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

- [ ] Connect grouped search to `GET /search/`.
- [ ] Connect track-only search to `GET /search/tracks/`.
- [ ] Connect autocomplete to `GET /search/autocomplete/`.
- [ ] Connect trending terms to `GET /search/trending/`.
- [ ] Preserve Nepali Unicode and Romanized search behavior.
- [ ] Add debounce, cancellation, pagination, empty, and error tests.

### Phase 6 — Authentication and account

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

The following checks passed after the homepage and public-catalog integration:

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
- Tests: 45 passed across 14 files
- Next.js production build: passed
- Diff whitespace validation: passed

These are local checks. They do not replace browser-level staging verification,
which remains blocked by the deployed CORS configuration.

## Recommended next action

Resolve the backend CORS and HTTPS origin configuration first. Then perform a
browser smoke test of the completed homepage and public catalog before beginning
the Search phase. This separates deployment connectivity failures from search
implementation failures and gives the remaining phases a verified API baseline.
