# SunneKatha Frontend–Backend Integration Analysis

**Analysis date:** 2026-07-29
**Phase:** 1 — discovery and contract analysis only
**Repository:** one combined repository containing the Next.js frontend at the
repository root and the Django backend in `backend/`

No application code, environment configuration, API behavior, or mock data was
changed during this phase.

## Contract sources inspected

- Frontend routes, feature components, shared components, TypeScript types,
  services, TanStack Query keys, Zustand stores, environment reader, API client,
  local media, and mock data.
- Backend root and application URL configurations, DRF views, serializers,
  filters, services, settings, permissions, and API tests.
- A temporary OpenAPI schema generated with
  `python manage.py spectacular --settings=config.settings.test --validate`.
  The generated schema validated and documented 123 operations. The repository
  does not store a generated schema file; the running application exposes
  `/api/schema/`, `/api/docs/`, and `/api/redoc/`.

The backend API prefix is `/api/v1`. A frontend base URL should therefore include
the prefix, for example `http://13.205.30.123/api/v1` during temporary
development. The IP must remain environment configuration, not application
source, and must be replaced by an HTTPS domain before production use.

## 1. Frontend mock and temporary files

### Mock catalog and user data

| File | Data owned | Main consumers |
| --- | --- | --- |
| `src/data/tracks.ts` | 24 tracks, embedded author/narrator summaries, local artwork and one shared audio URL | Track, catalog, author, narrator, playlist, search, library services |
| `src/data/playlists.ts` | Editorial-style playlists with fully embedded tracks | Playlist, author, narrator, search, library services |
| `src/data/authors.ts` | Authors with `popularTracks` | Author, search, library services |
| `src/data/narrators.ts` | Narrators with `narratedTracks` | Narrator, search, library services |
| `src/data/genres.ts` | Genre records | Catalog and search services |
| `src/data/moods.ts` | Mood records | Catalog and search services |
| `src/data/library.ts` | Favorite, saved, followed, recently played, and progress defaults | Track and library services |
| `src/data/index.ts` | Barrel export for all mock records | All mock-backed services |

### Mock transport and fake behavior

- `src/services/mock-api.ts` introduces artificial latency and URL/local-storage
  scenarios for success, empty, error, and loading states.
- `src/services/profile-service.ts` contains hardcoded listening statistics.
- `src/services/auth-session.ts` is only an in-memory token placeholder. It has
  no login flow and its refresh function always returns `null`.
- `src/features/profile/preferences-store.ts` contains a fake profile
  (`anil@example.com`) and persists it locally.
- `src/features/library/library-store.ts` implements fake favorite, saved,
  followed, recent, and progress mutations in local storage.
- `src/services/progress-service.ts` writes progress and recently played state
  only to the local library store.
- `src/features/player/player-store.ts` persists the queue and player settings
  locally; it does not synchronize with the backend.

### Temporary media and artwork

- `public/audio/sunnekatha-demo.mp3`
- `public/audio/demo-placeholder.wav`
- `public/audio/README.md`
- `public/images/demo/demo-author.webp`
- `public/images/demo/folk-tale-lakhe.webp`
- `public/images/demo/himalayan-letter.webp`
- `public/images/demo/monsoon-literature.webp`
- `public/images/demo/moonlit-listening.webp`

Every mock track currently points directly to
`/audio/sunnekatha-demo.mp3`. These files must remain until all player and card
consumers use backend-mapped content and stream authorization. Generic fallback
artwork should be introduced or explicitly retained separately from demo catalog
artwork.

### Explicit mock configuration

`.env.example` currently defaults `NEXT_PUBLIC_API_MODE=mock`.
`src/config/environment.ts` also defaults unknown or absent mode values to
`mock`, and defaults the API base URL to
`http://localhost:8000/api/v1`. Remote adapters are not implemented.

## 2. Components consuming mock data

Components do not import `src/data` directly. Pages call service functions
through TanStack Query, and those services import mock data. This is a useful
boundary for migration.

| UI/feature | Mock-backed queries or behavior |
| --- | --- |
| `src/features/home/home-page.tsx` | Featured playlists, continue listening, trending, recent, popular authors/narrators, mood playlists |
| `src/features/explore/explore-page.tsx` | Filtered releases, genres, moods, featured playlists, authors, narrators |
| `src/features/search/search-page.tsx` | Grouped local search and hardcoded trending terms |
| `src/features/track/track-detail-page.tsx` | Track, author, narrator, and locally calculated similar tracks |
| `src/features/playlist/playlist-detail-page.tsx` | Fully embedded mock playlist |
| `src/features/author/author-detail-page.tsx` | Author, tracks, locally derived playlists, related authors |
| `src/features/narrator/narrator-detail-page.tsx` | Narrator, tracks, locally derived playlists |
| `src/features/library/library-page.tsx` | One fake aggregate library and the entire mock catalog |
| `src/features/profile/profile-settings-page.tsx` | Hardcoded listening statistics and locally persisted preferences |
| `src/features/player/audio-engine.tsx` | Direct `Track.audioUrl`, local resume/progress/history |
| Cards, queue panel, and player panels | Receive mock-derived domain objects through props/store state |

There are no direct network calls in React components. The only production
`fetch` call is centralized in `src/services/api-client.ts`.

Routes currently implemented are `/`, `/explore`, `/search`, `/library`,
`/playlists`, `/playlist/[slug]`, `/track/[slug]`, `/author/[slug]`,
`/narrator/[slug]`, and `/profile`. There are no frontend literary-work,
album-detail, genre-detail, mood-detail, authentication, creator, or upload
routes yet.

## 3. Frontend service methods

| Service | Existing method | Current return |
| --- | --- | --- |
| Track | `getTrendingTracks()` | `Track[]` |
| Track | `getRecentlyAddedTracks()` | `Track[]` |
| Track | `getContinueListening()` | `ContinueListeningItem[]` |
| Track | `getTrackBySlug(slug)` | `Track \| null` |
| Track | `getSimilarTracks(trackId, limit?)` | `Track[]` |
| Playlist | `getFeaturedPlaylists()` | `Playlist[]` |
| Playlist | `getMoodPlaylists()` | `Playlist[]` |
| Playlist | `getPlaylistBySlug(slug)` | `Playlist \| null` |
| Author | `getPopularAuthors()` | `Author[]` |
| Author | `getAuthorBySlug(slug)` | `Author \| null` |
| Author | `getAuthorTracks(authorId)` | `Track[]` |
| Author | `getAuthorFeaturedCollections(authorId)` | `Playlist[]` |
| Author | `getRelatedAuthors(authorId, limit?)` | `Author[]` |
| Narrator | `getPopularNarrators()` | `Narrator[]` |
| Narrator | `getNarratorBySlug(slug)` | `Narrator \| null` |
| Narrator | `getNarratorTracks(narratorId)` | `Track[]` |
| Narrator | `getNarratorFeaturedPlaylists(narratorId)` | `Playlist[]` |
| Catalog | `getExploreTracks(filters?)` | `Track[]` |
| Catalog | `getGenres()` | `Genre[]` |
| Catalog | `getMoods()` | `Mood[]` |
| Search | `searchContent(request)` | `SearchResults` |
| Search | `getTrendingSearches()` | `string[]` |
| Library | `getInitialUserLibrary()` | One aggregate `UserLibrary` |
| Library | `getLibraryCatalog()` | All tracks/playlists/authors/narrators |
| Profile | `getListeningStatistics()` | Hardcoded display statistics |
| Progress | `saveListeningProgress(input)` | Synchronous local record |
| Progress | `getSavedProgress(trackId)` | Synchronous local record |
| Progress | `getResumePosition(trackId)` | Synchronous seconds |
| Progress | `recordRecentlyPlayed(trackId)` | Synchronous local mutation |

No frontend service currently exists for registration/login/logout, current
user, profile mutation, relationship mutation, user playlist mutation,
playback sessions, server queue synchronization, stream authorization,
subscriptions, creator APIs, or upload sessions.

### Existing query keys

Query-key groups exist for home, explore, search, tracks, playlists, authors,
narrators, library, and profile. Missing groups include authentication/current
user, albums, literary works, taxonomy detail, favorites, saved playlists,
follows, progress detail, history, queue, stream access, and uploads.

All queries use a global one-minute stale time, no focus refetch, and one retry.
Authenticated queries are not yet gated by authentication because authentication
does not exist.

## 4. Required backend endpoints

The current UI requires these first:

- Aggregated homepage and optional personalized continue-listening.
- Explore track filtering plus genres, moods, featured playlists, popular
  authors, and popular narrators.
- Grouped search and trending searches.
- Track, playlist, author, and narrator slug details.
- Tracks by author/narrator and related tracks.
- Stream authorization before assigning an audio element source.
- Current-user library relationships and listening progress.

The requested complete integration additionally requires:

- Registration, login, token refresh, logout, current user, profile,
  preferences, and password change.
- Literary-work and album list/detail endpoints and corresponding frontend
  routes.
- Favorite/save/follow list and mutation endpoints.
- Playlist CRUD, add/remove/reorder/visibility/duplicate.
- Playback sessions, recently played, and history.
- Queue restore and synchronization.
- Creator upload request/status/confirm/cancel.
- Creator track metadata/review/processing APIs where a creator UI is added.

## 5. Actual backend endpoints

All paths below are relative to `/api/v1`.

### Public and aggregated

| Area | Endpoint |
| --- | --- |
| Homepage | `GET /home/` |
| Explore aggregate | `GET /explore/` |
| Explore tracks | `GET /explore/tracks/` |
| Tracks | `GET /tracks/`, `/tracks/featured/`, `/tracks/trending/`, `/tracks/recent/` |
| Track relations | `GET /tracks/content-type/{value}/`, `/tracks/author/{slug}/`, `/tracks/narrator/{slug}/`, `/tracks/genre/{slug}/`, `/tracks/mood/{slug}/` |
| Track detail | `GET /tracks/{slug}/`, `/tracks/{slug}/related/`, `/tracks/{slug}/player/` |
| Stream authorization | `GET /tracks/{slug}/stream/?quality=auto|low|high` |
| Works | `GET /works/`, `/works/featured/`, `/works/{slug}/` |
| Albums | `GET /albums/`, `/albums/featured/`, `/albums/{slug}/` |
| Authors | `GET /authors/`, `/authors/featured/`, `/authors/{slug}/` |
| Narrators | `GET /narrators/`, `/narrators/featured/`, `/narrators/{slug}/` |
| Playlists | `GET /playlists/`, `/playlists/featured/`, `/playlists/{slug}/` |
| Taxonomy | `GET /genres/`, `/moods/`, `/languages/`, `/content-categories/` |
| Search | `GET /search/`, `/search/tracks/`, `/search/autocomplete/`, `/search/trending/` |

### Authentication

| Operation | Endpoint and body |
| --- | --- |
| Register | `POST /auth/register/` with `email`, `username`, `displayName`, `password`, `passwordConfirm` |
| Login | `POST /auth/login/` (alias `/auth/token/`) with `email`, `password` |
| Refresh | `POST /auth/token/refresh/` with `refresh` |
| Logout | `POST /auth/logout/` with `refresh`, Bearer access token |
| Current user | `GET /auth/me/` |
| Profile | `PATCH /auth/profile/` |
| Preferences | `PATCH /auth/preferences/` |
| Password | `POST /auth/change-password/` |

### Library and listener state

| Operation | Endpoint |
| --- | --- |
| Favorite list/mutation | `GET /library/tracks/`; `POST|PUT|DELETE /library/tracks/{uuid}/favorite/` |
| Saved playlist list/mutation | `GET /library/playlists/`; `POST|PUT|DELETE /library/playlists/{uuid}/save/` |
| Followed author list/mutation | `GET /library/authors/`; `POST|PUT|DELETE /library/authors/{uuid}/follow/` |
| Followed narrator list/mutation | `GET /library/narrators/`; `POST|PUT|DELETE /library/narrators/{uuid}/follow/` |
| Progress | `GET|PUT|PATCH|DELETE /me/listening-progress/{track_uuid}/` |
| Complete/remove | `POST .../{track_uuid}/complete/`; `DELETE .../{track_uuid}/remove/` |
| Continue listening | `GET /me/continue-listening/` |
| Playback sessions | `POST /me/playback-sessions/`; `PATCH /me/playback-sessions/{uuid}/`; `POST .../{uuid}/end/` |
| Recent/history | `GET /me/recently-played/`; `GET /me/listening-history/` |
| Queue | `GET|PUT|DELETE /me/queue/`; item add/remove, play-next, reorder, position, shuffle, and repeat subroutes |

### Playlist mutations

- `POST /playlists/`
- `PATCH|DELETE /playlists/{slug}/`
- `POST /playlists/{slug}/tracks/add/` with `trackId`
- `POST|DELETE /playlists/{slug}/tracks/remove/` with `trackId`
- `POST|PATCH /playlists/{slug}/tracks/reorder/` with ordered `trackIds`
- `PATCH /playlists/{slug}/visibility/`
- `POST /playlists/{slug}/duplicate/`

### Uploads and creator APIs

- `POST /uploads/` requests a presigned upload.
- `GET /uploads/{session_uuid}/` reads status.
- `POST /uploads/{session_uuid}/confirm/` verifies the object.
- `POST /uploads/{session_uuid}/cancel/` cancels.
- `/creator/` provides creator profile, tracks, drafts, uploads, processing
  status, metadata update, review submission, approval, and analytics.

## 6. Frontend TypeScript types

The frontend domain layer is camelCase and UI-oriented:

- `Track` requires `audioUrl`, non-null `coverImage`, embedded author and
  narrator summaries, slug arrays for genres/moods, duration seconds, and
  optional waveform/transcript/literary work.
- `Playlist` requires description, embedded tracks, count, duration, curator,
  category, and cover.
- `Author` requires biography, genre strings, and embedded `popularTracks`.
- `Narrator` requires biography, follower count, and embedded
  `narratedTracks`.
- `UserLibrary` is one aggregate of ID arrays, recent IDs, and progress.
- `SearchResults` contains tracks, playlists, authors, narrators, genres, and
  moods, but no literary works or albums.
- `AuthenticatedUser` currently contains only `id`, `email`, and
  `displayName`.
- Pagination types already match the backend envelope and use `pageSize`.

Raw API response types and mapping functions do not yet exist. Domain types are
currently used as if they were transport types.

## 7. Backend serializer response structures

The backend intentionally exposes many frontend-compatible camelCase aliases.

- Compact track: `id`, `slug`, `title`, `titleEnglish`, `subtitle`,
  `contentType`, `author`, `narrator`, nullable `coverImage`, `duration`,
  `language`, `genres`, `moods`, `playCount`, `isPremium`, `isExplicit`,
  `isFeatured`, `publishedAt`.
- Detailed track adds descriptions, chapter/track numbers, waveform,
  transcript, processing status, literary work, album, and timestamps.
- Stream response: `quality`, `url`, nullable `expiresAt`, compact `track`,
  and `authorization`.
- Compact playlist omits description and tracks. Detail adds both.
- Author detail does not embed tracks or genres.
- Narrator detail does not embed narrated tracks.
- Work and album serializers are available, but the current frontend has no
  corresponding domain models/pages.
- Homepage: `{hero, sections}`. Each section has `id`, localized titles, and
  heterogeneous `items`; authenticated users may receive continue listening.
- Explore: `{sections}` with heterogeneous item types.
- Search: `{query, tracks, literaryWorks, playlists, albums, authors,
  narrators, genres, moods}`.
- Library list endpoints use standard pagination. Relationship mutations return
  `{id, is_favorited|is_playlist_saved|is_author_followed|is_narrator_followed}`.
- Progress and queue fields are already camelCase.
- Upload request returns session metadata plus `upload`, the S3 presigned POST
  instructions.

## 8. Field-name mismatches

| Frontend expectation | Backend behavior | Required handling |
| --- | --- | --- |
| `Track.audioUrl` always present | Compact/detail tracks never expose an audio URL | Make `audioUrl` runtime player state or optional; request `/stream/` on play |
| `coverImage: string` | Track, playlist, taxonomy, author, narrator, album images may be null/blank | Mapper must apply generic non-demo fallback artwork |
| Full `Author.popularTracks` | Author detail has no embedded tracks | Compose with `/tracks/author/{slug}/`; do not use author UUID |
| Full `Narrator.narratedTracks` | Narrator detail has no embedded tracks | Compose with `/tracks/narrator/{slug}/` |
| `Author.genres` | Author serializer has no genres | Derive only if required from related content, or make optional |
| Full playlist everywhere | List/home/search return compact playlists | Use separate compact/detail domain types or fetch detail on navigation |
| Search excludes works/albums | Backend grouped search includes both | Extend frontend result types and UI deliberately |
| Search result filter names | Backend canonical names include `works`; frontend union does not | Align query filter union and tabs |
| `getAuthorTracks(authorId)` | Endpoint accepts author slug | Change adapter signature/caller to slug |
| `getNarratorTracks(narratorId)` | Endpoint accepts narrator slug | Change adapter signature/caller to slug |
| Similar tracks use track ID | Endpoint accepts track slug | Change adapter signature/caller to slug |
| One aggregate `UserLibrary` | Four paginated relationship lists plus history/progress endpoints | Replace aggregate service with parallel authenticated queries |
| `isFavorited` style expected for domain flags | Library serializers currently return snake_case flags | Map at API boundary |
| `autoplay` and `allowExplicitContent` | User API uses `autoplayEnabled`, `explicitContentEnabled` | Preference mapper/form payload required |
| Frontend profile theme/audio quality | Backend user preferences do not store these | Keep as explicitly local preferences |
| `LiteraryWorkSummary` lacks `id`, `slug`, `titleEnglish`, `contentType` | Backend returns these fields | Expand the frontend summary type |
| `Playlist.category` | Backend exposes both `category` and `playlistType` | Prefer `playlistType`; retain mapped `category` only for existing UI |
| `Track.waveform` | Backend source is `waveform_data`, exposed as `waveform` | Compatible after nullable validation |
| Error status is `number \| null` | Requested example says `number` | Existing nullable status is appropriate for offline/abort failures |

The backend already uses camelCase compatibility aliases for core catalog and
account responses, so a global snake-to-camel conversion should not be added.
Use endpoint-specific raw types and explicit mappers.

## 9. Missing backend functionality

No blocking backend endpoint is missing for the currently implemented homepage,
explore, search, track, playlist, author, narrator, library, player,
progress/history, queue, authentication, or upload objectives.

Gaps or product decisions remain:

- There is no backend endpoint equivalent to the mock listening-statistics cards
  for ordinary users. Staff analytics endpoints are not an appropriate
  substitute.
- There are no dedicated “author featured collections,” “related authors,” or
  “narrator featured playlists” endpoints. These UI sections should be derived
  from available public queries only if bounded and semantically sound, hidden
  when unsupported, or proposed as additive backend endpoints after documenting
  the need.
- The frontend lacks literary-work, album, genre, and mood detail pages even
  though the backend exposes work and album detail.
- Upload sessions are not directly linked to a track by the public upload
  request contract; creator metadata/review flow must define how a confirmed
  object becomes or updates a draft.
- Subscription plan/list/purchase APIs are intentionally absent; the backend
  supports entitlements and staff-managed subscriptions, not payments.
- CloudFront signing code exists, but the supplied deployment notes say signed
  streaming is pending. Live stream readiness must be verified against deployed
  environment configuration rather than inferred from source.

## 10. Authentication compatibility

The backend uses Simple JWT bearer authentication, not session-cookie
authentication:

- Access lifetime defaults to 15 minutes.
- Refresh lifetime defaults to 7 days.
- Refresh tokens rotate and old tokens are blacklisted.
- Protected requests use `Authorization: Bearer <access>`.
- Refresh responses can contain both a new access and rotated refresh token.
- Logout blacklists the submitted refresh token and requires an access token.
- Password change blacklists all outstanding tokens.
- Active-user permission checks protect account and listener endpoints.

The frontend API client already retries one original request and coalesces
concurrent refresh attempts, but its adapter is a placeholder. It must persist
the rotated refresh token, clear all auth/user state after failed refresh, and
never send authenticated queries for anonymous users.

Because JWT is sent in a header, DRF API requests do not depend on Django CSRF
cookies. Django Admin remains CSRF/session protected. Token storage remains a
security decision: browser-readable persistent refresh tokens increase XSS
impact; in-memory-only tokens do not survive reloads. The existing backend does
not issue HttpOnly auth cookies, so a cookie-only frontend cannot be implemented
without a documented backend contract change.

Do not use real passwords over the temporary HTTP endpoint.

## 11. Pagination compatibility

- Standard page pagination is
  `{count, next, previous, results}`.
- Default page size is 20; `pageSize` is accepted and capped at 100.
- Cursor pagination is `{next, previous, results}` with `cursor` and `pageSize`.
- Taxonomy endpoints disable pagination and return arrays.
- Homepage, explore, grouped search, autocomplete, trending search, stream,
  relationship mutation, progress detail, queue, and upload operations have
  custom non-page envelopes.

Frontend services currently return bare arrays for all lists. Each adapter must
either return a domain pagination object or explicitly unwrap `results` for
bounded rails. Infinite/catalog pages should preserve page metadata rather than
discard it.

## 12. Error-response compatibility

The backend global exception handler returns:

```json
{
  "detail": "Validation failed.",
  "code": "validation_error",
  "errors": {
    "fieldName": ["Message"]
  }
}
```

Non-validation failures omit `errors`. Unexpected exceptions become a safe
`server_error` message. The frontend `normalizeApiError` already understands
this structure, preserves field errors, and maps network/abort failures.

Improvements needed during implementation:

- Distinguish timeout from user cancellation where practical.
- Add explicit UI handling for 429 and optionally parse `Retry-After`.
- Do not retry most mutations automatically.
- Ensure failed refresh clears persisted user-sensitive state.
- Do not display unknown raw error messages originating from arbitrary thrown
  frontend errors as if they were safe backend text.
- Add FormData/presigned-upload handling; the current client always JSON
  stringifies bodies.

## 13. Audio-player compatibility

Current player behavior:

- `HTMLAudioElement` is mounted globally above routes.
- `Track.audioUrl` is assigned synchronously when the selected track changes.
- Queue, play/pause, seek, volume, speed, shuffle, and repeat are Zustand state.
- Resume position is local.
- Progress is saved every 15 seconds, on pause, track change, end, page hide,
  unload, and unmount.
- Completion is local at 90%, matching the backend threshold.
- Recently played is recorded locally as soon as a track is selected.

Required integration:

1. Select a compact/detail track without a private URL.
2. Request `GET /tracks/{slug}/stream/?quality=auto`.
3. On authorization success, assign `response.url` to the audio element.
4. Retain `expiresAt` and refresh only when necessary.
5. Treat 403 as premium/login entitlement denial, 404 as unavailable or hidden,
   400 as unavailable quality, and 503 as media delivery unavailable.
6. Never construct S3 or CloudFront object paths in the frontend.

The stream service returns stable unsigned CloudFront URLs for free published
tracks and short-lived signed URLs for premium/unpublished authorized access.
The backend never proxies bytes. The player’s `audioUrl` requirement is the
largest domain-model incompatibility and should be addressed before catalog
objects enter the player store.

The older `/tracks/{slug}/player/` response exposes a `media` quality map and is
backed by the same CloudFront service, but `/stream/` provides authorization and
expiration metadata and should be the primary player flow.

## 14. Upload-workflow compatibility

Backend flow:

1. Authenticated creator or authorized staff posts `uploadType`,
   `originalFilename`, `contentType`, and `expectedSize` to `/uploads/`.
2. Backend validates extension/type/size, generates the object key, and returns
   session metadata plus presigned POST instructions in `upload`.
3. Browser sends multipart form data directly to the returned S3 URL using all
   returned form fields.
4. Browser posts to `/{sessionId}/confirm/`.
5. Backend verifies existence, size, content type, encryption, and file
   signature before confirming.
6. Status can be read and a pending upload can be canceled.

The frontend has no upload UI, types, client, or progress implementation. The
central JSON API client should request/confirm/cancel sessions, while S3 transfer
needs a separate narrowly scoped uploader that follows the returned method,
URL, and fields exactly. It must not add the API Bearer token to S3.

Browser upload remains blocked until the active frontend HTTPS origin is added
to the bucket’s restrictive CORS configuration. Wildcard CORS is not acceptable.
The response currently includes `objectKey` as session metadata; frontend code
must treat it as opaque and never construct or display private media URLs from
it.

## 15. Integration risks

### Blocking/high

1. **Temporary HTTP API and production CORS conflict.** Production settings
   require HTTPS CORS and CSRF origins. An HTTPS frontend calling the HTTP API
   also encounters browser mixed-content blocking. Do not weaken production
   settings; complete domain/TLS configuration.
2. **Player contract is asynchronous.** Existing UI assumes every `Track` has a
   playable URL. Catalog migration without a stream-resolution state would
   break playback or leak infrastructure assumptions.
3. **No implemented auth session.** Protected queries and mutations cannot be
   integrated safely until rotated refresh-token state and logout/failure
   cleanup are defined.
4. **Heterogeneous homepage/explore sections.** Items need discriminated raw
   types or identifier-based mappers; blindly casting JSON to existing card
   models is unsafe.
5. **Nullable media fields.** Existing Next Image/audio consumers assume valid
   strings.

### Medium

6. Public list services currently expect arrays, while backend lists paginate.
7. Current library initialization merges fake defaults with local user state;
   retaining this behavior after login could contaminate real accounts.
8. Author/narrator detail UI expects relationships the detail endpoints do not
   embed.
9. Local and server queue/progress conflict resolution is undefined.
10. The current API client lacks FormData and separates neither cancellation nor
    timeout errors.
11. Regular users have no equivalent to the mock profile listening statistics.
12. Search must add works/albums and map compact result shapes.
13. Image URLs may be relative, absolute S3/CloudFront URLs, or null depending
    on storage configuration and serializer.
14. Anonymous homepage should not request the protected continue-listening
    endpoint separately; use the aggregate response and auth gating.

### Deployment-dependent

15. CloudFront implementation exists, while deployment notes describe it as
    pending. Verify `/stream/` with a non-sensitive development track.
16. S3 browser CORS awaits the final frontend origin.
17. Temporary backend content may be sparse; empty-state behavior must not be
    mistaken for contract failure.

## 16. Recommended implementation order

1. Preserve this analysis as the contract baseline.
2. Make remote API mode explicit and production-safe; add a local ignored
   environment file for the temporary base URL and document the HTTPS blocker.
3. Harden the central API client: raw response validation, FormData support,
   timeout classification, 429 handling, and a complete auth adapter.
4. Define raw endpoint types and explicit mappers for compact/detail track,
   playlist, author, narrator, taxonomy, homepage, explore, search, user,
   progress, queue, stream, and upload responses.
5. Integrate anonymous homepage using the single aggregate endpoint.
6. Integrate public explore/catalog rails and pagination.
7. Integrate track, playlist, author, and narrator details; hide unsupported
   related sections rather than fabricating content.
8. Integrate grouped search, autocomplete, track pagination, and trending.
9. Add real authentication/current-user/profile/preference flows.
10. Replace local fake library initialization with authenticated relationship
    queries and mutations.
11. Resolve stream access before assigning audio sources; then connect server
    progress and playback sessions without blocking playback.
12. Add queue synchronization with local-last-modified versus server
    `updatedAt` conflict rules.
13. Add user playlist operations.
14. Add creator uploads only after frontend-origin S3 CORS is approved.
15. Add missing work/album/genre/mood routes as separate reviewable UI changes.
16. Remove migrated mock code incrementally, run checks after every area, then
    perform the final no-fallback audit.

## 17. Safe mock-file removal order

Do not delete the `src/data` barrel first; it would create a broad,
hard-to-review break.

1. **Homepage:** migrate home service and remove only its mock service imports.
2. **Explore/taxonomy:** migrate catalog service; retain records still used by
   search, details, library, or tests.
3. **Public details:** migrate track, playlist, author, and narrator services.
4. **Search:** migrate search service and remove runtime imports of all catalog
   mock records.
5. **Authentication/profile:** remove fake profile defaults only after
   hydration from current-user data; retain local-only theme/audio-quality
   defaults.
6. **Library:** replace fake aggregate and local toggle behavior; then remove
   `src/data/library.ts`.
7. **Player:** remove `audioUrl` from catalog fixtures only after stream
   authorization and player loading/error behavior are tested.
8. **Individual mock data modules:** delete only after `rg` confirms there are
   no production imports. Move any still-useful fixtures into test-only files.
9. **Temporary media/artwork:** delete demo audio and catalog artwork only after
   no production or test reference remains and generic fallbacks exist.
10. **Mock transport:** delete `mock-api.ts`, mock scenarios, README guidance,
    and mock-mode environment switches last. If explicit mock mode is retained,
    isolate it in a development adapter, default it to false, and reject it in
    production.

Automated player/store tests currently import `src/data`; those fixtures should
move into test-specific factories before the corresponding data modules are
deleted.

## Phase 1 conclusion

The backend covers nearly all requested integration capabilities and already
uses frontend-oriented camelCase aliases in core serializers. The work is not a
simple base-URL switch: the frontend needs an explicit transport/domain mapping
layer, complete JWT session handling, pagination-aware services, heterogeneous
section parsing, and asynchronous media authorization.

No backend compatibility change is justified before those frontend adapters are
implemented. The only potential additive endpoint needs are ordinary-user
listening statistics and optional author/narrator collection recommendations;
both should be evaluated after the supported UI is integrated.
