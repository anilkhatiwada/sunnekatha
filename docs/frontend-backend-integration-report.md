# SunneKatha frontend–backend integration report

Date: 2026-07-23

## Executive summary

The Django API covers the core catalog, authentication, playlists, library,
progress, playback history, queue, homepage, explore, and search capabilities.
It is not yet a drop-in replacement for the Next.js mock services.

The frontend services still read `src/data` through `mockApiResponse`; none of
the product service methods currently call `apiClient`. Connecting the API
therefore requires a frontend adapter milestone, which is outside this task.
No frontend files were changed.

The main blocking integration issue is audio delivery. The frontend assigns
`Track.audioUrl` directly to `HTMLAudioElement.src`. Django intentionally does
not expose an `audioUrl` in track metadata: the client must call
`GET /api/v1/tracks/{slug}/stream/?quality=auto`, then assign the returned
short-lived CloudFront `url`. This must remain a two-step flow for premium
authorization and URL expiry.

Compatibility changes made during this review:

- search accepts both backend parameters (`q`, `type`, `content_type`) and
  frontend names (`query`, `resultType`, `contentType`);
- track list and detail payloads include `subtitle`;
- `literaryWork.type` now matches the frontend's `novel | collection` union,
  while `literaryWork.contentType` retains the precise catalog classification;
- author detail includes `birthYear` and `deathYear` alongside `birthDate` and
  `deathDate`.

## Contract conventions

| Concern | Frontend | Django API | Assessment |
| --- | --- | --- | --- |
| Base URL | Configured API base URL | `/api/v1/` | Compatible when the environment includes `/api/v1`. |
| JSON names | camelCase | Public serializers use camelCase aliases | Compatible. |
| Identity | String IDs and slug detail URLs | UUID IDs and slug detail URLs | Compatible; IDs remain opaque strings. |
| Dates | ISO 8601 strings | DRF ISO 8601 | Compatible. |
| Durations | Seconds | Seconds | Compatible. |
| Authentication | Optional Bearer token with one refresh retry | Simple JWT access/rotated refresh tokens | Compatible after implementing the frontend session adapter. |
| Pagination | `{count,next,previous,results}` | Same shape; `page`, `pageSize`, maximum 100 | Compatible, but current mock service methods return arrays and must unwrap `results`. |
| Errors | `{detail?,code?,errors?}` | Standardized `{detail,code,errors?}` | Compatible. |
| Detail 404 | Service promises `null` | API returns normalized 404 error | Frontend adapter must catch `ApiError.status === 404` and return `null`. |

## Frontend service method audit

### Author service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `getPopularAuthors()` | `GET /authors/featured/` or the `popular-authors` homepage/explore section | Partial. Backend results are compact and paginated; frontend `Author` requires `genres` and embedded `popularTracks`. Use a summary type in the future adapter or hydrate tracks separately. |
| `getAuthorBySlug(slug)` | `GET /authors/{slug}/` | Partial. Identity, names, image, biography, and life years match. Backend does not embed `genres` or `popularTracks`; the frontend already makes a separate track request. Adapter must supply an empty/default genres collection or derive it. |
| `getAuthorTracks(authorId)` | `GET /tracks/author/{authorSlug}/` | Capability exists, identifier differs. The frontend method receives an ID, while the endpoint filters by slug. The adapter should retain the author slug from the detail response or the backend can later add an ID alias if necessary. Response is paginated. |
| `getAuthorFeaturedCollections(authorId)` | No dedicated endpoint | Missing. Public playlist list cannot currently filter by author. This should be added only when the frontend switches from mocks and the desired “featured collection” semantics are confirmed. |
| `getRelatedAuthors(authorId, limit)` | No dedicated endpoint | Missing. No stable backend ranking contract exists yet. |

### Narrator service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `getPopularNarrators()` | `GET /narrators/featured/` or homepage/explore section | Partial. Backend is compact and paginated; frontend `Narrator` requires embedded `narratedTracks`. |
| `getNarratorBySlug(slug)` | `GET /narrators/{slug}/` | Partial. Profile fields match, but `narratedTracks` is intentionally not nested. |
| `getNarratorTracks(narratorId)` | `GET /tracks/narrator/{narratorSlug}/` | Capability exists, identifier differs; response is paginated. |
| `getNarratorFeaturedPlaylists(narratorId)` | No dedicated endpoint | Missing. Playlist list has no narrator filter. |

### Catalog and explore service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `getExploreTracks(filters)` | `GET /explore/tracks/?contentType=&genre=&mood=` | Compatible after unwrapping pagination. The backend additionally supports language, author, narrator, premium, explicit, and ordering filters. |
| `getGenres()` | `GET /genres/` | Compatible fields; response is paginated rather than a bare array. |
| `getMoods()` | `GET /moods/` | Compatible fields; response is paginated rather than a bare array. |

The aggregated `GET /explore/` endpoint can replace several independent
collection requests, but its section-based response is not the return type of
any current frontend method.

### Playlist service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `getFeaturedPlaylists()` | `GET /playlists/featured/` | Partial. List payloads are intentionally compact and paginated; they do not embed `description` or `tracks`. Cards have the required identity/artwork/count fields. |
| `getMoodPlaylists()` | Mood collections are returned by `/home/` and `/explore/`; no equivalent hard-coded playlist set | Semantic mismatch. The frontend mock selects three slugs, while the backend models moods and editorial sections explicitly. |
| `getPlaylistBySlug(slug)` | `GET /playlists/{slug}/` | Compatible. Detail includes ordered compact tracks, descriptions, counts, duration, curator, category, and featured state. A 404 must be converted to `null` by the adapter. |

Playlist detail visibility also matches the intended security model: public
playlists are listed, unlisted playlists are available by direct slug, and
private playlists are owner-only.

### Track and homepage service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `getTrendingTracks()` | `GET /tracks/trending/` or the homepage section | Compatible after pagination unwrap, except for `audioUrl`; see player flow. |
| `getRecentlyAddedTracks()` | `GET /tracks/recent/` or the homepage section | Compatible after pagination unwrap, except for `audioUrl`. |
| `getContinueListening()` | `GET /me/continue-listening/` | Compatible shape and ordering; authentication is required. Backend progress additionally returns `progressPercentage` and `lastListenedAt`. |
| `getTrackBySlug(slug)` | `GET /tracks/{slug}/` | Compatible metadata after the additive subtitle/work changes, except for `audioUrl`. A 404 must become `null`. |
| `getSimilarTracks(trackId, limit)` | `GET /tracks/{slug}/related/` | Capability exists, but the route uses the source slug and standard pagination rather than an ID plus `limit`. |

`GET /home/` works anonymously and inserts continue listening for authenticated
users. Its section-based aggregate can reduce frontend requests, but the current
home page calls seven independent mock methods and does not consume this shape.

### Search service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `searchContent({query,resultType})` | `GET /search/?query=&resultType=` | Compatible after this review. All groups are always present; non-selected groups are empty. Backend also returns `literaryWorks` and `albums`, which clients may ignore. Entity groups use compact payloads, so author/narrator/playlist results do not satisfy the current overly broad full-detail TypeScript types. |
| `getTrendingSearches()` | `GET /search/trending/` | Compatible after reading the `searches` property. |

Track-only pagination is available at `GET /search/tracks/`. Autocomplete is
available at `GET /search/autocomplete/`. Nepali Unicode, English, trigram
matching, and explicit Romanized aliases are supported.

### Library service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `getInitialUserLibrary()` | No single aggregate endpoint | Partial capability. Favorites, saved playlists, followed authors/narrators, recently played, and progress exist as separate authenticated endpoints. The current `UserLibrary` expects ID arrays and up to 50 progress records. |
| `getLibraryCatalog()` | Public track, playlist, author, and narrator lists | No equivalent aggregate endpoint. A full unpaginated catalog would be unsafe; the future frontend adapter should fetch only the visible saved entities or paginated collections. |

The absence of these two aggregates is intentional rather than an invitation to
return the complete catalog in one response. A dedicated lightweight library
bootstrap endpoint may be added later if one round trip is a measured need.

### Profile service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `getListeningStatistics()` | No user-facing endpoint | Missing. Existing analytics endpoints are staff-only aggregate reporting and must not be exposed as personal statistics. |

### Local progress service

| Frontend method | Backend mapping | Result |
| --- | --- | --- |
| `saveListeningProgress(input)` | `PUT` or `PATCH /me/listening-progress/{trackId}/` with `{progressSeconds,durationSeconds}` | Payload and 90% completion behavior match. The current method is synchronous/local-first; network sync must be fire-and-forget or queued without delaying player state. |
| `getSavedProgress(trackId)` | `GET /me/listening-progress/{trackId}/` | Response matches the frontend fields plus harmless additional fields. Local state should remain the immediate source during playback. |
| `getResumePosition(trackId)` | Derived client-side from the progress response | Compatible. Completed tracks resume at zero. |
| `recordRecentlyPlayed(trackId)` | Playback session/history endpoints, not a direct ID mutation | Partial. Start/update/end playback sessions produce history without requiring per-second events. |

The frontend sends progress every 15 seconds and on pause, track change, end,
and exit. That cadence matches the backend design. Negative and materially
over-duration positions receive validation errors; small overshoots are clamped.

## Authentication integration

Authentication endpoints are:

- `POST /auth/register/`
- `POST /auth/login/` (also `/auth/token/`)
- `POST /auth/token/refresh/`
- `POST /auth/logout/`
- `GET /auth/me/`
- `PATCH /auth/profile/`
- `PATCH /auth/preferences/`
- `POST /auth/change-password/`

Login accepts `{email,password}` and returns `{access,refresh,user}`. Refresh
accepts `{refresh}` and returns a new access token and, with rotation enabled, a
new refresh token. Logout requires both the Bearer access token and
`{refresh}`.

The frontend `apiClient` retry logic is compatible, but its placeholder
`refreshAccessToken()` always returns `null`. Authenticated requests must set
`requiresAuth: true`; otherwise no token is attached and a 401 will not trigger
refresh. Tokens should be stored by a concrete session adapter before protected
services are connected.

## Player URL flow

Required integration sequence:

1. Load track metadata from a list/detail endpoint.
2. Immediately before playback, call
   `GET /tracks/{slug}/stream/?quality=auto`.
3. Set the audio element source to response `url`.
4. Retain `expiresAt`; request a new URL when it expires or playback receives an
   authorization-related media failure.
5. Never persist or share premium signed URLs.

Free published tracks work anonymously. Premium tracks require an active
entitlement. Unpublished tracks are hidden except from authorized staff or their
creator. Django returns JSON metadata and never proxies audio bytes.

`GET /tracks/{slug}/player/` exposes high/low media URL candidates, but the
stream endpoint is the preferred authorization contract because it returns
quality, expiry, and authorization state explicitly.

## Playlist actions

All mutation endpoints require authentication. Only owners may modify user
playlists; editorial management remains staff-only.

| Action | Request | Response |
| --- | --- | --- |
| Create | `POST /playlists/` with `titleNe`, optional `titleEn`, descriptions, cover, visibility | Full playlist detail, 201 |
| Update | `PATCH /playlists/{slug}/` with editable fields | Full playlist detail |
| Delete | `DELETE /playlists/{slug}/` | 204 |
| Add track | `POST /playlists/{slug}/tracks/add/` with `{trackId}` | Full playlist detail |
| Remove track | `POST /playlists/{slug}/tracks/remove/` with `{trackId}` | Full playlist detail |
| Reorder | `PATCH /playlists/{slug}/tracks/reorder/` with `{trackIds}` | Full playlist detail |
| Visibility | `PATCH /playlists/{slug}/visibility/` with `{visibility}` | Full playlist detail |
| Duplicate | `POST /playlists/{slug}/duplicate/` with optional `{titleNe}` | Full private user playlist, 201 |

The current frontend has no HTTP playlist mutation service. Its local store
actions cannot be swapped directly for these asynchronous operations.

## Library actions

All operations require authentication and are idempotent.

| Relationship | Add | Remove | List |
| --- | --- | --- | --- |
| Favorite track | `POST` or `PUT /library/tracks/{id}/favorite/` | `DELETE` same URL | `GET /library/tracks/` |
| Save playlist | `POST` or `PUT /library/playlists/{id}/save/` | `DELETE` same URL | `GET /library/playlists/` |
| Follow author | `POST` or `PUT /library/authors/{id}/follow/` | `DELETE` same URL | `GET /library/authors/` |
| Follow narrator | `POST` or `PUT /library/narrators/{id}/follow/` | `DELETE` same URL | `GET /library/narrators/` |

Mutation responses contain the target `id` and relationship flag. List
responses are paginated compact entities. The frontend currently toggles local
state synchronously; a future adapter should use optimistic updates with
rollback on API failure.

## Queue synchronization

All queue endpoints are under `/me/queue/` and require authentication:

| Action | Method and payload |
| --- | --- |
| Get | `GET /me/queue/` |
| Replace | `PUT /me/queue/` with `{trackIds,currentIndex,positionSeconds}` |
| Clear | `DELETE /me/queue/` |
| Append | `POST /me/queue/items/` with `{trackId}` |
| Play next | `POST /me/queue/play-next/` with `{trackId}` |
| Remove | `DELETE /me/queue/items/{queueItemId}/` |
| Reorder | `PATCH /me/queue/reorder/` with every `{itemIds}` in desired order |
| Position | `PATCH /me/queue/position/` with `{currentIndex,positionSeconds}` |
| Shuffle | `PATCH /me/queue/shuffle/` with `{isShuffleEnabled}` |
| Repeat | `PATCH /me/queue/repeat/` with `{repeatMode}` |

The response embeds ordered compact tracks and stable server queue-item IDs.
Duplicate tracks are allowed. The frontend remains immediate source of truth;
sync should be debounced and used for restoration, not performed on every
playback tick.

The frontend `QueueItem` optionally contains `source`; the backend does not
persist this field. The frontend also persists playback speed and volume, while
the server queue intentionally stores neither. Account preferences separately
store default playback speed.

## Error handling

The global exception handler returns:

```json
{
  "detail": "Validation failed.",
  "code": "validation_error",
  "errors": {
    "fieldName": ["Explanation"]
  }
}
```

This matches `normalizeApiError`. Authentication, permission, not-found,
throttling, and server errors use the same envelope. Field names follow the
request contract, generally camelCase.

The frontend client correctly handles 204 responses and avoids parsing an empty
body. It also combines caller abort signals with request timeout. Remaining
frontend requirements are to convert expected detail 404s to `null`, configure
refresh storage, and mark protected calls with `requiresAuth`.

## Remaining integration risks

1. **Blocking: player adapter.** Direct `Track.audioUrl` playback cannot consume
   the secure stream authorization response.
2. **Blocking: services remain mock-backed.** No product service currently calls
   `apiClient`.
3. **High: broad frontend entity types.** List/search cards expect full
   `Author`, `Narrator`, and `Playlist` objects, while production list APIs
   correctly return compact representations. Introduce frontend summary types
   during the integration milestone rather than reintroducing large nested
   payloads.
4. **High: ID/slug method mismatch.** Author, narrator, and related-track mock
   methods receive IDs while public relation routes use slugs.
5. **Medium: missing editorial relationships.** Author collections, related
   authors, and narrator playlists have no dedicated APIs.
6. **Medium: library bootstrap.** The frontend expects a single ID aggregate;
   Django exposes normalized paginated resources.
7. **Medium: personal statistics.** The profile mock has no privacy-safe
   user-facing equivalent.
8. **Low: taxonomy image fields.** Backend taxonomy payloads include additional
   image and metadata fields; clients may ignore them.

## Recommended frontend integration order

No frontend work was performed, but the safest future sequence is:

1. implement JWT session storage and refresh;
2. add response adapters for pagination and expected 404s;
3. split compact and detail TypeScript types;
4. implement the stream-URL handshake in the audio engine;
5. connect read-only catalog/search/home routes;
6. add local-first progress and queue synchronization;
7. add optimistic playlist and library mutations;
8. decide whether the missing aggregate/editorial endpoints are still needed
   after measuring real frontend request patterns.
