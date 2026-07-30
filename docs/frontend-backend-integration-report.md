# SunneKatha frontend–backend integration report

**Updated:** 2026-07-30

**Frontend:** Next.js 16 App Router

**Backend:** Django REST Framework under `/api/v1`

**Production frontend:** `https://sunnekatha.com`

**Production API:** `https://api.sunnekatha.com/api/v1`

## Outcome

The public catalog, account, library, playback, playlist, search, notification,
creator, and direct-upload flows are connected through the frontend service
boundary. Mock mode remains available for isolated UI development; production
uses remote mode.

Two small backend compatibility additions were made:

- `GET /playlists/?mine=true` lists the authenticated user's public, unlisted,
  and private user playlists.
- `GET /tracks/` accepts `work` and `album` slug filters so work and album detail
  routes can load ordered tracks without client-side catalog downloads.
- The Google `SocialIdentity` model is registered read-only in Admin so the
  existing all-domain-model registration invariant remains valid.

No private S3 object key is used as a playable URL. Audio playback always starts
from the media-access endpoint and receives a CloudFront URL.

## Route and service coverage

| Frontend area | Backend contract | Status |
| --- | --- | --- |
| Homepage | `GET /home/` | Integrated, anonymous and personalized |
| Explore tracks | `GET /explore/tracks/` | Integrated with content type, genre, mood, language, premium, explicit, author, narrator, and ordering service filters |
| Genres and moods | `GET /genres/`, `GET /moods/` | Integrated |
| Track detail/related | `GET /tracks/{slug}/`, `GET /tracks/{slug}/related/` | Integrated |
| Work detail | `GET /works/{slug}/` + `GET /tracks/?work={slug}` | Integrated |
| Album detail | `GET /albums/{slug}/` + `GET /tracks/?album={slug}` | Integrated |
| Author detail/tracks | `GET /authors/{slug}/`, `GET /tracks/author/{slug}/` | Integrated |
| Narrator detail/tracks | `GET /narrators/{slug}/`, `GET /tracks/narrator/{slug}/` | Integrated |
| Public playlists | `GET /playlists/`, featured and slug detail | Integrated |
| User playlists | create, patch, delete, add/remove/reorder, visibility, duplicate | Integrated |
| Grouped search | `GET /search/` | Integrated, including works and albums |
| Track search | `GET /search/tracks/` | Integrated with pagination |
| Autocomplete/trending | `/search/autocomplete/`, `/search/trending/` | Integrated |
| Google login | `POST /auth/google/` | Integrated |
| Email registration/login | `/auth/register/`, `/auth/login/` | Integrated |
| Token refresh/logout | `/auth/token/refresh/`, `/auth/logout/` | Integrated |
| Profile/preferences/password | `/auth/profile/`, `/auth/preferences/`, `/auth/change-password/` | Integrated |
| Favorites/saves/follows | `/library/...` idempotent relationship endpoints | Integrated with optimistic state and rollback |
| Library lists | `/library/tracks/`, playlists, authors, narrators | Integrated |
| Continue listening | `GET /me/continue-listening/` | Integrated, including removal |
| Recently played/history | `/me/recently-played/`, `/me/listening-history/` | Integrated |
| Listening progress | `PUT /me/listening-progress/{trackId}/` | Local-first integration |
| Playback sessions | start, patch, end under `/me/playback-sessions/` | Integrated |
| Queue sync | `/me/queue/` and state endpoints | Integrated with debounce and restoration |
| Notifications | list, unread count, read, read-all | Integrated |
| Creator center | profile, drafts, uploads, submit for review | Integrated |
| Direct S3 uploads | request, browser-to-S3 POST, confirm/cancel | Integrated |

## Authentication behavior

- Account-only navigation is hidden until a current user is available.
- Protected pages use `AuthRequired`.
- Access and rotated refresh tokens are stored in tab-scoped
  `sessionStorage`, not persistent local storage.
- Authenticated requests add a Bearer access token.
- One shared refresh request prevents refresh storms during concurrent 401s.
- Failed refresh clears the local session.
- Logout blacklists the refresh token when the backend is reachable and clears
  the local session even when it is not.
- Google login and email/password login establish the same frontend session.

The current token storage is safer than persistent local storage but still
accessible to JavaScript. Moving refresh tokens to secure, HttpOnly,
same-site cookies would require an intentional backend authentication-contract
change.

## Pagination and errors

- DRF page responses are unwrapped only inside services.
- Track-only search retains `count` and next-page behavior.
- Library and creator screens request bounded pages.
- Expected detail 404 responses map to existing not-found states.
- Other API errors use `ApiError`, including normalized field errors,
  throttling metadata, timeout errors, and safe user-facing messages.
- Protected service failures do not silently turn into mock content.

## Player and media flow

1. Catalog endpoints return metadata without a private storage URL.
2. A user playback action requests
   `GET /tracks/{slug}/stream/?quality=auto`.
3. The returned free or signed CloudFront URL is mapped into an in-memory
   playable track.
4. Collection playback resolves ordered track access before replacing the
   immediate player queue.
5. If a URL expires or fails, the audio engine requests one fresh URL for the
   current track, preserves the playback position, and updates both the current
   track and queue source.
6. Django never proxies audio bytes.

Queue state stores track identity and restoration position on the backend. The
frontend remains the immediate playback source of truth and synchronizes queue
changes after a short debounce, plus position snapshots every 30 seconds.

Progress is sent every 15 seconds by the existing player behavior and at
important transitions. Playback sessions and history remain separate from the
single progress row per user/track.

## Playlist behavior

- Anonymous users can view public and direct unlisted playlists.
- Private playlists remain owner-only.
- `mine=true` requires authentication and never exposes another user's
  playlists.
- Owners can create, edit, change visibility, add/remove tracks, reorder with
  stable server positions, duplicate, and delete with confirmation.
- Compact playlist cards load detail only after playback intent, avoiding large
  nested list payloads.
- Editorial playlist permissions remain enforced by Django.

## Direct S3 upload flow

The creator upload screen:

1. sends filename metadata, MIME type, size, and upload type to Django;
2. receives a server-controlled key and presigned POST fields;
3. sends the file directly to S3 using every signed field;
4. asks Django to confirm the object;
5. cancels the upload session after a failed direct transfer where possible.

AWS credentials, presigned fields, and object keys are never displayed in the
UI. Upload access remains creator/staff-only.

## Design review

The visual system remains consistent with the existing warm, literary
direction:

- dark charcoal background and warm surface hierarchy;
- orange primary actions and restrained gold accents;
- Noto Devanagari typography with comfortable Nepali line height;
- compact list tables and responsive card grids;
- protected navigation removed rather than disabled before login;
- full-page empty, loading, error, and retry states;
- keyboard-labelled player, queue, search, playlist, notification, and upload
  controls.

The login and public layouts were visually inspected in the local application
at the available laptop viewport. Breakpoint rules use stacked forms/grids below
`sm`, hide the fixed desktop sidebar below `lg`, and retain bottom spacing for
the mini-player/mobile navigation.

## Validation

The final change was validated with:

- `npm run typecheck`
- `npm run lint`
- `npm test`
- `npm run build`
- `python manage.py check --settings=config.settings.test`
- `python manage.py makemigrations --check --dry-run --settings=config.settings.test`
- focused Django playlist and track API tests
- full Django suite: 608 tests

Exact final totals are recorded in `docs/frontend-integration-status.md`.

## Remaining limitations

These are deliberate product or backend limitations, not disconnected existing
APIs:

1. Offline downloads are not exposed because no secure public download endpoint
   exists yet.
2. Payment checkout is not implemented; the backend intentionally has no payment
   provider integration.
3. Email and push notification delivery are placeholders by backend design.
4. Creator upload confirmation does not automatically create a catalog track;
   editorial staff must associate and review uploaded media.
5. Personal listening statistics do not have a privacy-scoped user API; staff
   analytics remain in Django Admin.
6. Author-related playlists, narrator-related playlists, and related-author
   ranking have no dedicated public endpoint.
7. Mock mode does not synthesize full work and album detail records; those new
   detail routes are production-API features.

## Recommended follow-up

- Review the 11 high-severity findings reported by the production `npm ci`
  audit and upgrade affected dependencies in a tested dependency-hardening
  change; do not use an unreviewed force upgrade in production.
- Add end-to-end browser tests using a seeded test API for registration,
  playlist management, playback resume, queue restoration, and direct S3 upload.
- Add a secure user download contract only after entitlement, expiry, and
  offline-storage rules are agreed.
- Consider HttpOnly refresh cookies in a future authentication hardening
  milestone.
- Add a creator endpoint that explicitly associates a confirmed upload with a
  draft track if self-service draft creation becomes a product requirement.
