# SunneKatha Frontend API Analysis

## Purpose and scope

This document records the backend contract implied by the existing Next.js
frontend. It is based on the TypeScript types, mock data and services, TanStack
Query keys, application routes, Zustand stores, player audio engine, and the
existing `docs/api-contract.md`.

No Django models, serializers, views, migrations, or remote service adapters are
introduced here. The recommended API preserves the frontend's camelCase field
names and current response shapes unless a limitation is explicitly identified.

Current contract conventions:

- Base path: `/api/v1`
- JSON fields: camelCase
- IDs: opaque strings
- Detail lookups exposed by the UI: stable slugs
- Dates and timestamps: ISO 8601 strings
- Duration and progress: seconds
- Authentication header: `Authorization: Bearer <access-token>`
- Not-found detail services: translate HTTP `404` to `null`
- Standard error: `{ "detail"?, "code"?, "errors"? }`

## 1. Existing frontend models

### Shared primitives

```ts
type ContentType =
  | "poem"
  | "story"
  | "essay"
  | "novel_chapter"
  | "folk_tale"
  | "drama";

type Language = "ne" | "en";
```

`Genre` and `Mood` have the same current shape:

```ts
interface GenreOrMood {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  description: string;
}
```

### Track structures

```ts
interface AuthorSummary {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  image: string;
}

interface NarratorSummary {
  id: string;
  slug: string;
  name: string;
  image: string;
}

interface LiteraryWorkSummary {
  title: string;
  type: "novel" | "collection";
  chapterNumber?: number;
}

interface Track {
  id: string;
  slug: string;
  title: string;
  subtitle?: string;
  description?: string;
  contentType: ContentType;
  author: AuthorSummary;
  narrator: NarratorSummary;
  coverImage: string;
  audioUrl: string;
  duration: number;
  publishedAt: string;
  language: Language;
  genres: string[];
  moods: string[];
  playCount: number;
  isPremium: boolean;
  isExplicit: boolean;
  waveform?: number[];
  transcript?: string;
  literaryWork?: LiteraryWorkSummary;
}
```

`genres` and `moods` on a track are currently strings used for display,
filtering, similarity scoring, and search. They are not `Genre` or `Mood`
objects. The mock values should be checked before deciding whether those strings
represent slugs, labels, or stable keys.

### Playlist structures

```ts
interface Playlist {
  id: string;
  slug: string;
  title: string;
  description: string;
  coverImage: string;
  curatorName: string;
  trackCount: number;
  totalDuration: number;
  tracks: Track[];
  category: string;
  isFeatured: boolean;
}
```

Mock playlists are built from ordered track ID lists. `trackCount` and
`totalDuration` are derived from `tracks`, while the frontend expects all three
fields in a playlist response. Track order is significant for queue playback.

### Author structures

```ts
interface Author extends AuthorSummary {
  biography: string;
  birthYear?: number;
  deathYear?: number;
  genres: string[];
  popularTracks: Track[];
}
```

`popularTracks` is embedded and is used directly when playing from author cards.
Author detail pages also request a separate, complete author-track list.

### Narrator structures

```ts
interface Narrator extends NarratorSummary {
  biography: string;
  followerCount: number;
  narratedTracks: Track[];
}
```

`narratedTracks` is embedded and is used directly when playing from narrator
cards. Narrator detail pages also request a separate narrated-track list.

### Search result structures

```ts
type SearchResultType =
  | "all"
  | "tracks"
  | "playlists"
  | "authors"
  | "narrators"
  | "genres"
  | "moods";

interface SearchRequest {
  query: string;
  resultType?: SearchResultType;
}

interface SearchResults {
  tracks: Track[];
  playlists: Playlist[];
  authors: Author[];
  narrators: Narrator[];
  genres: Genre[];
  moods: Mood[];
}
```

An empty or whitespace-only query returns all six keys with empty arrays. A
type-filtered search also preserves all six keys and empties the five
non-selected collections. Search currently matches normalized Nepali/English
text across titles, descriptions, people, genre and mood values, curator names,
and categories.

### Library and progress structures

```ts
interface ListeningProgress {
  trackId: string;
  progressSeconds: number;
  durationSeconds: number;
  isCompleted: boolean;
  updatedAt: string;
}

interface UserLibrary {
  favoriteTrackIds: string[];
  savedPlaylistIds: string[];
  followedAuthorIds: string[];
  followedNarratorIds: string[];
  recentlyPlayedTrackIds: string[];
  listeningProgress: ListeningProgress[];
}

interface ContinueListeningItem {
  track: Track;
  progress: ListeningProgress;
}

interface LibraryCatalog {
  tracks: Track[];
  playlists: Playlist[];
  authors: Author[];
  narrators: Narrator[];
}
```

The local library store persists these ID collections and progress records under
`sunnekatha-library`. Initialization merges server/mock IDs with local IDs once
per persisted installation. Recent tracks are de-duplicated, newest-first, and
capped at 20. Progress is one record per track, newest-first in normal writes,
and capped at 50.

The player clamps progress to `0..duration`, ignores saves before one second or
when duration is not positive, and marks a track complete at 90%. It records
progress approximately every 15 seconds, on track changes, pause/stop-related
transitions, track end, page exit, and audio-engine cleanup. Incomplete progress
is used as the resume position; completed progress resumes at zero. Starting a
track immediately moves its ID to the front of recently played.

### Queue and player structures relevant to the API

```ts
interface QueueItem {
  id: string;
  track: Track;
  addedAt: string;
  source?: string;
}
```

Queue state, playback speed, volume, and repeat mode are client state and do not
currently require backend persistence. Queue items embed complete tracks. The
player's current time and playing state are intentionally not persisted.

### API utility and authentication structures

```ts
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface CursorPaginatedResponse<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

interface AuthenticatedUser {
  id: string;
  email: string;
  displayName: string;
}
```

Login expects `{ email, password }` and returns
`{ access, refresh, user }`. Refresh expects `{ refresh }` and returns
`{ access, refresh? }`.

Profile preferences currently include `displayName`, `email`,
`preferredLanguage`, `autoplay`, `defaultPlaybackSpeed`,
`allowExplicitContent`, `themePreference`, and a persisted `audioQuality` fixed
to `"automatic"`. Listening statistics are currently presentation strings:
`{ id, label, value, detail }`.

### Frontend routes and TanStack Query keys

The implemented public-facing routes are `/`, `/explore`, `/search`, `/library`,
`/playlists`, `/profile`, `/playlist/[slug]`, `/track/[slug]`,
`/author/[slug]`, and `/narrator/[slug]`. Explore accepts `type`, `genre`, and
`mood`; search accepts `q`.

Central query-key families are:

- `home`: featured playlists, continue listening, trending tracks, recently
  added, popular authors, popular narrators, and mood playlists
- `explore`: releases plus filter object, moods, genres, featured playlists,
  popular authors, and popular narrators
- `search`: results plus `{ query, resultType }`, and trending terms
- `tracks`: detail by slug and similar by track ID
- `playlists`: detail by slug
- `authors`: detail by slug, tracks/collections/related by author ID
- `narrators`: detail by slug, tracks/playlists by narrator ID
- `library`: initial library and the full mock catalog
- `profile`: listening statistics

Backend mutations must invalidate the relevant `library` keys and any composed
home/continue-listening or profile statistics keys once remote adapters exist.

## 2. Existing mock service methods

| Service method | Parameters | Current return | Current behavior |
| --- | --- | --- | --- |
| `getTrendingTracks` | none | `Track[]` | Sorts by `playCount`, first 12 |
| `getRecentlyAddedTracks` | none | `Track[]` | Sorts by `publishedAt`, first 12 |
| `getContinueListening` | none | `ContinueListeningItem[]` | Incomplete progress, newest update first |
| `getTrackBySlug` | `slug` | `Track \| null` | Exact slug lookup |
| `getSimilarTracks` | `trackId`, `limit = 6` | `Track[]` | Scores type, genres, moods, author, then popularity |
| `getFeaturedPlaylists` | none | `Playlist[]` | Filters `isFeatured` |
| `getMoodPlaylists` | none | `Playlist[]` | Hard-coded set of three playlist slugs |
| `getPlaylistBySlug` | `slug` | `Playlist \| null` | Exact slug lookup with embedded tracks |
| `getPopularAuthors` | none | `Author[]` | Embedded-track play-count total, first 8 |
| `getAuthorBySlug` | `slug` | `Author \| null` | Exact slug lookup |
| `getAuthorTracks` | `authorId` | `Track[]` | Popularity descending |
| `getAuthorFeaturedCollections` | `authorId` | `Playlist[]` | Contains author's tracks, first 6 |
| `getRelatedAuthors` | `authorId`, `limit = 6` | `Author[]` | Shared genres then popularity |
| `getPopularNarrators` | none | `Narrator[]` | `followerCount` descending, first 8 |
| `getNarratorBySlug` | `slug` | `Narrator \| null` | Exact slug lookup |
| `getNarratorTracks` | `narratorId` | `Track[]` | Popularity descending |
| `getNarratorFeaturedPlaylists` | `narratorId` | `Playlist[]` | Contains narrator's tracks, first 6 |
| `getExploreTracks` | optional `{ contentType, genre, mood }` | `Track[]` | AND filters, newest first |
| `getGenres` | none | `Genre[]` | All mock genres |
| `getMoods` | none | `Mood[]` | All mock moods |
| `searchContent` | `{ query, resultType = "all" }` | `SearchResults` | Grouped normalized search |
| `getTrendingSearches` | none | `string[]` | Static terms |
| `getInitialUserLibrary` | none | `UserLibrary` | Static user library |
| `getLibraryCatalog` | none | `LibraryCatalog` | Complete tracks/playlists/authors/narrators |
| `saveListeningProgress` | `{ trackId, progressSeconds, durationSeconds }` | `ListeningProgress \| null` | Synchronous local upsert |
| `getSavedProgress` | `trackId` | `ListeningProgress \| null` | Synchronous local lookup |
| `getResumePosition` | `trackId` | `number` | Zero for missing/completed progress |
| `recordRecentlyPlayed` | `trackId` | `void` | Synchronous local update |
| `getListeningStatistics` | none | inferred statistics array | Static display values |

All asynchronous mock services return structured clones and support global
loading, success, empty, and error test scenarios. No service currently calls
the network.

## 3. Required backend endpoints

The following endpoints preserve existing service responsibilities. Array
responses are retained for bounded editorial sections; unbounded collections use
pagination.

### Authentication

| Method | Endpoint | Purpose | Response |
| --- | --- | --- | --- |
| `POST` | `/auth/token/` | Login | `LoginResponse` |
| `POST` | `/auth/token/refresh/` | Refresh access | `RefreshTokenResponse` |
| `POST` | `/auth/logout/` | End session | `204` |
| `GET` | `/auth/me/` | Current identity | `AuthenticatedUser` |

### Catalog and discovery

| Method | Endpoint | Query | Response |
| --- | --- | --- | --- |
| `GET` | `/tracks/` | `page`, `pageSize`, `contentType`, `genre`, `mood`, `ordering` | `PaginatedResponse<Track>` |
| `GET` | `/tracks/trending/` | `limit` | `Track[]` |
| `GET` | `/tracks/recent/` | `limit` | `Track[]` |
| `GET` | `/tracks/{slug}/` | — | `Track`; `404` maps to `null` |
| `GET` | `/tracks/{id}/similar/` | `limit` | `Track[]` |
| `GET` | `/playlists/` | `page`, `pageSize`, `featured`, `mood`, `category` | `PaginatedResponse<Playlist>` |
| `GET` | `/playlists/featured/` | `limit` | `Playlist[]` |
| `GET` | `/playlists/moods/` | `limit` or `mood` | `Playlist[]` |
| `GET` | `/playlists/{slug}/` | — | `Playlist`; `404` maps to `null` |
| `GET` | `/authors/` | `page`, `pageSize`, `ordering` | `PaginatedResponse<Author>` |
| `GET` | `/authors/popular/` | `limit` | `Author[]` |
| `GET` | `/authors/{slug}/` | — | `Author`; `404` maps to `null` |
| `GET` | `/authors/{id}/tracks/` | `page`, `pageSize`, `ordering` | `PaginatedResponse<Track>` |
| `GET` | `/authors/{id}/collections/` | `limit` | `Playlist[]` |
| `GET` | `/authors/{id}/related/` | `limit` | `Author[]` |
| `GET` | `/narrators/` | `page`, `pageSize`, `ordering` | `PaginatedResponse<Narrator>` |
| `GET` | `/narrators/popular/` | `limit` | `Narrator[]` |
| `GET` | `/narrators/{slug}/` | — | `Narrator`; `404` maps to `null` |
| `GET` | `/narrators/{id}/tracks/` | `page`, `pageSize`, `ordering` | `PaginatedResponse<Track>` |
| `GET` | `/narrators/{id}/playlists/` | `limit` | `Playlist[]` |
| `GET` | `/genres/` | — | `Genre[]` |
| `GET` | `/moods/` | — | `Mood[]` |
| `GET` | `/search/` | `q`, `type`, pagination parameters | `SearchResults` or clarified paginated variant |
| `GET` | `/search/trending/` | `limit` | `string[]` |
| `GET` | `/home/` | optional `locale` | Optional composed home payload |

`/playlists/moods/` is added because `getMoodPlaylists` is a distinct frontend
service expectation but the previous contract only exposed a general playlist
filter. It may instead be implemented as `/playlists/?mood=...` if the remote
adapter composes the current multi-playlist section without changing page code.

### Authenticated library, progress, and profile

| Method | Endpoint | Purpose | Response |
| --- | --- | --- | --- |
| `GET` | `/me/library/` | Initial ID-based library snapshot | `UserLibrary` |
| `POST` / `DELETE` | `/me/favorites/tracks/{trackId}/` | Add/remove favorite | `204` |
| `POST` / `DELETE` | `/me/playlists/{playlistId}/save/` | Save/unsave playlist | `204` |
| `POST` / `DELETE` | `/me/authors/{authorId}/follow/` | Follow/unfollow author | `204` |
| `POST` / `DELETE` | `/me/narrators/{narratorId}/follow/` | Follow/unfollow narrator | `204` |
| `GET` | `/me/recently-played/` | Ordered activity | cursor-paginated track/activity records |
| `POST` | `/me/recently-played/{trackId}/` | Record start/recent play | `204` |
| `GET` | `/me/listening-progress/` | Progress history | `CursorPaginatedResponse<ListeningProgress>` |
| `PUT` | `/me/listening-progress/{trackId}/` | Idempotent progress upsert | `ListeningProgress` |
| `GET` | `/me/continue-listening/` | Optional server-composed rail | cursor-paginated `ContinueListeningItem` |
| `GET` | `/me/listening-statistics/` | Profile statistics | statistics array |
| `GET` | `/me/preferences/` | Load preferences | `ProfilePreferences` |
| `PATCH` | `/me/preferences/` | Update preferences | `ProfilePreferences` |

The current `getLibraryCatalog` mock should not become a production endpoint
that returns the entire catalog. Remote library views should resolve their
entities through paginated catalog endpoints or a bounded composed library
payload.

## 4. Expected request payloads

GET filters are query parameters and do not have JSON bodies.

### Authentication

```json
{
  "email": "listener@example.com",
  "password": "user-supplied-password"
}
```

```json
{
  "refresh": "opaque-refresh-token"
}
```

Logout may accept `{ "refresh": "opaque-refresh-token" }` if refresh tokens are
sent in JSON. If refresh uses an HttpOnly cookie, logout should invalidate the
cookie/session without exposing the token to JavaScript.

### Listening progress

`PUT /me/listening-progress/{trackId}/`

```json
{
  "progressSeconds": 486,
  "durationSeconds": 1288
}
```

The backend should validate non-negative numeric values, clamp progress, use the
catalog track duration as authoritative when available, calculate completion at
90% or more, and treat retries as idempotent upserts. The frontend may send an
older update after network delay; conflict policy needs a timestamp or monotonic
rule before synchronization is implemented.

### Library mutations

Favorite, save, and follow endpoints currently need no body because the target
ID and desired state are encoded by method and URL. Recording a recent play also
needs no body for current behavior. A future activity event could add
`startedAt`, `source`, or device information only after the frontend contract is
expanded.

### Preferences

`PATCH /me/preferences/` accepts any subset of:

```json
{
  "displayName": "अनिल खटिवडा",
  "email": "anil@example.com",
  "preferredLanguage": "ne",
  "autoplay": true,
  "defaultPlaybackSpeed": 1,
  "allowExplicitContent": false,
  "themePreference": "dark",
  "audioQuality": "automatic"
}
```

Current frontend validation requires a trimmed display name of 2–50 characters,
a valid email, language `ne|en`, playback speed `0.5..2`, and theme
`dark|light|system`. The player store itself permits speed through 3, which is a
contract mismatch to resolve.

## 5. Expected response payloads

### Track detail example

```json
{
  "id": "track-001",
  "slug": "stable-human-readable-slug",
  "title": "नेपाली शीर्षक",
  "subtitle": "Optional subtitle",
  "description": "Optional description",
  "contentType": "poem",
  "author": {
    "id": "author-001",
    "slug": "author-slug",
    "name": "लेखकको नाम",
    "nameEnglish": "Optional English Name",
    "image": "/media/authors/author.webp"
  },
  "narrator": {
    "id": "narrator-001",
    "slug": "narrator-slug",
    "name": "वाचकको नाम",
    "image": "/media/narrators/narrator.webp"
  },
  "coverImage": "/media/tracks/cover.webp",
  "audioUrl": "/media/audio/track.mp3",
  "duration": 598,
  "publishedAt": "2026-07-15T18:10:00.000Z",
  "language": "ne",
  "genres": ["कविता"],
  "moods": ["शान्त"],
  "playCount": 1200,
  "isPremium": false,
  "isExplicit": false,
  "waveform": [0.2, 0.7, 0.4],
  "transcript": "Optional transcript",
  "literaryWork": {
    "title": "Optional parent work",
    "type": "collection",
    "chapterNumber": 1
  }
}
```

Optional properties may be omitted. If the backend emits `null`, frontend types
must be widened or serializers must omit the field; `undefined` does not exist
in JSON.

### Playlist, author, and narrator responses

Playlist detail must contain ordered, complete `tracks`, plus `trackCount` and
`totalDuration`. Author responses currently contain complete `popularTracks`;
narrator responses contain complete `narratedTracks`. For immediate
compatibility, list and detail endpoints should return those fields, although
summary serializers are strongly recommended as a coordinated future frontend
change to reduce payloads.

### Search response

```json
{
  "tracks": [],
  "playlists": [],
  "authors": [],
  "narrators": [],
  "genres": [],
  "moods": []
}
```

All keys must be present even when empty. `type=tracks`, for example, should
still return the other five keys as empty arrays unless the frontend adapter
normalizes a narrower server response.

### User library and progress

```json
{
  "favoriteTrackIds": ["track-001"],
  "savedPlaylistIds": ["playlist-001"],
  "followedAuthorIds": ["author-001"],
  "followedNarratorIds": ["narrator-001"],
  "recentlyPlayedTrackIds": ["track-002", "track-001"],
  "listeningProgress": [
    {
      "trackId": "track-002",
      "progressSeconds": 486,
      "durationSeconds": 1288,
      "isCompleted": false,
      "updatedAt": "2026-07-18T21:15:00.000Z"
    }
  ]
}
```

An individual progress upsert returns the normalized `ListeningProgress`
record. Recent IDs must be ordered most-recent-first.

### Pagination and errors

```json
{
  "count": 42,
  "next": "https://api.example.com/api/v1/tracks/?page=3",
  "previous": "https://api.example.com/api/v1/tracks/?page=1",
  "results": []
}
```

```json
{
  "detail": "Human-readable explanation",
  "code": "stable_machine_code",
  "errors": {
    "email": ["Enter a valid email address."]
  }
}
```

## 6. Pagination requirements

- Use page-number pagination for general tracks, playlists, authors, narrators,
  and author/narrator track lists.
- Preserve request names `page` and `pageSize`; do not expose DRF's default
  `page_size` without frontend normalization.
- Use cursor pagination for recently played, listening progress, continue
  listening, and other append-only activity feeds. Order by a stable
  `(updatedAt, id)` or equivalent tuple to avoid duplicates.
- Editorial sections such as trending, recent, popular, featured, related, and
  collections are bounded arrays controlled by `limit`; defaults should match
  mocks: 12 tracks, 8 people, and 6 related/collection results.
- Genres and moods are small taxonomies and may remain unpaginated.
- Playlist detail tracks are currently an unpaginated ordered array. If
  playlists can become large, the frontend must be changed before paginating
  this field because queue replacement expects the complete ordered list.
- Grouped search pagination is unresolved. One shared `page` cannot paginate six
  independently sized collections coherently. Recommended behavior is a bounded
  grouped response for `type=all` and a normal paginated single collection for a
  specific type, with an adapter preserving `SearchResults`.
- `next` and `previous` must consistently be either absolute URLs, relative
  URLs, or opaque cursors according to their response type. The existing generic
  types allow strings but do not define traversal behavior yet.

## 7. Authentication requirements

- Catalog, detail, explore, taxonomy, and general search endpoints should be
  public unless premium metadata policy requires otherwise.
- All `/me/*` endpoints and library mutations require authentication.
- Authentication currently assumes bearer access tokens. The API client adds
  the header only when a service sets `requiresAuth: true`.
- On a `401`, the API client performs one deduplicated refresh attempt and
  retries the original request once. A second failure clears the session through
  the configured adapter.
- Refresh-token storage is not implemented. Preferred production design is an
  HttpOnly, Secure, SameSite cookie through a same-origin backend or BFF.
- If cross-origin cookies are used, CSRF and CORS policy must be designed
  explicitly. Bearer-only JSON mutations still need tight allowed origins and
  must never expose tokens in URLs or logs.
- Login, logout, registration, payments, and real premium entitlements are
  outside the current frontend milestone. The placeholder authentication
  endpoints document future compatibility, not implemented UI.
- Anonymous users currently have a fully local persisted library. The product
  must decide whether login merges anonymous state into the account, replaces
  it, or prompts the user. The existing `initializeLibrary` behavior unions most
  IDs, gives local progress precedence, and cannot represent server-side
  removals.

## 8. Fields that need clarification

| Field or behavior | Clarification required |
| --- | --- |
| `Track.genres`, `Track.moods`, `Author.genres` | Are strings slugs, localized display names, or immutable keys? |
| `audioUrl`, `coverImage`, `image` | Absolute URL, API-relative URL, or site-relative path? Are signed audio URLs required? |
| `duration` vs `durationSeconds` | Track uses `duration`; progress uses `durationSeconds`. Confirm deliberate naming. |
| `publishedAt` | Publication date of literary work, audio release, or platform availability? |
| `playCount` | Raw global plays, qualified plays, or display-safe aggregate? |
| `isPremium` | What response/access behavior applies to unauthorized audio? |
| `isExplicit` | What content policy and preference filtering are required? |
| `waveform` | Normalization range, sample count, generation source, and list/detail inclusion. |
| `transcript` | Plain text or structured timed transcript; language and access policy. |
| `literaryWork` | Needs stable ID/slug if novels and collections become navigable backend entities. |
| `Playlist.category` | Free localized label or relation to a taxonomy? |
| Playlist membership | Need an explicit through model with position and uniqueness rules. |
| `curatorName` | Free text or user/editor relation? |
| `trackCount`, `totalDuration` | Stored values or computed serializer fields; update consistency. |
| `popularTracks`, `narratedTracks` | Maximum size, ordering rule, and whether list endpoints should embed them. |
| `followerCount` | Exact live count, cached aggregate, or rounded display value? |
| Search `type` | Confirm URL values exactly match plural `SearchResultType` values. |
| Search matching | Romanized Nepali requirements are documented but current normalization behavior and ranking contract need specification. |
| Progress conflicts | How to reject stale device updates; client does not currently send `updatedAt` or a version. |
| Completion | Backend contract says 90% using authoritative duration; define whether replay can make a completed item incomplete. |
| Recently played | Whether “started” is enough or a minimum listening threshold is required. |
| Library deletions | Current union merge resurrects server-removed items; deletion/tombstone strategy needed. |
| `audioQuality` | Currently only `"automatic"` and excluded from the form schema; confirm backend ownership. |
| Playback speed | Preferences allow max 2 while player state allows max 3. |
| Listening statistics | Current values are localized display strings; decide whether API returns raw metrics or presentation text. |
| Optional fields | Decide omitted versus explicit `null`; current TypeScript expects omission. |
| IDs | Confirm UUIDs or other opaque strings while retaining frontend `string`. |

## 9. Backend model mapping

These are conceptual mappings, not Django model definitions.

| Frontend contract | Suggested backend domain entity or projection |
| --- | --- |
| `Track` | Audio track/content release; foreign keys to author, narrator, optional literary work; taxonomy relations; media metadata |
| `AuthorSummary` | Summary serializer/projection of Author |
| `Author` | Author detail plus computed/limited popular-track projection |
| `NarratorSummary` | Summary serializer/projection of Narrator |
| `Narrator` | Narrator detail plus follower aggregate and narrated-track projection |
| `LiteraryWorkSummary` | Literary work parent projection; likely Novel or Collection entity |
| `Playlist` | Playlist plus ordered PlaylistTrack through records; derived count/duration |
| `Genre`, `Mood` | Separate taxonomy entities with stable slugs and localized labels |
| `UserLibrary.favoriteTrackIds` | User-to-Track favorite relation with timestamps |
| `savedPlaylistIds` | User-to-Playlist saved relation with timestamps |
| `followedAuthorIds` | User-to-Author follow relation with timestamps |
| `followedNarratorIds` | User-to-Narrator follow relation with timestamps |
| `recentlyPlayedTrackIds` | Listening activity or recent-play records ordered by occurrence |
| `ListeningProgress` | Unique user/track progress row with progress, completion, updated time, and concurrency metadata |
| `ContinueListeningItem` | Query projection joining incomplete progress to track |
| `AuthenticatedUser` | User/account API projection |
| `ProfilePreferences` | One-to-one user preferences/settings record |
| Listening statistics | Aggregated query/read model, preferably raw typed metrics |
| `SearchResults` | Search-layer projection across catalog entities, not a stored model |
| `QueueItem` | Client-only session object unless cross-device queue sync is later authorized |

Serializer names should preserve camelCase externally while backend persistence
may follow Python/Django snake_case. Avoid serializing full recursive object
graphs: track embeds only author/narrator summaries, never full people objects.

## 10. Compatibility risks

1. **Nested payload size:** playlists contain full tracks, authors contain full
   popular tracks, narrators contain full narrated tracks, and search returns
   all of them. This can become very large. Introduce summary types only through
   a coordinated frontend contract change.
2. **Pagination signature mismatch:** current mock methods return arrays, while
   scalable backend endpoints return pagination envelopes. Remote adapters must
   unwrap `results` or frontend service signatures must change deliberately.
3. **Search pagination ambiguity:** the current grouped `SearchResults` type has
   no count or cursor per group. A single page parameter cannot faithfully page
   every group.
4. **Library merge semantics:** local initialization unions IDs and gives local
   progress precedence. It can restore server-deleted saves/follows and overwrite
   newer cross-device progress.
5. **Progress ordering races:** updates contain no client timestamp, version, or
   idempotency key. Delayed 15-second writes can regress newer progress unless
   the backend has a conflict rule.
6. **Duration disagreement:** browser media duration, mock track duration, and
   backend authoritative duration may differ. Completion and clamping must be
   server-normalized, with the normalized record returned.
7. **Nullability:** optional TypeScript properties are not equivalent to JSON
   `null`. DRF defaults may emit `null` and break strict assumptions.
8. **Naming conversion:** automatic DRF snake_case responses would break the
   current camelCase frontend unless serializer fields or a renderer explicitly
   map names.
9. **Taxonomy identity:** localized genre/mood strings are fragile relationship
   keys and make locale changes, filtering, and search inconsistent.
10. **Detail identifier split:** public detail uses slug while related endpoints
    use ID. Router configuration must avoid collisions and adapters must encode
    both.
11. **Not-found behavior:** frontend detail services currently return `null`;
    generic API errors on `404` must be translated by each remote adapter.
12. **Authentication activation:** setting remote mode does not activate
    requests, and the placeholder refresh adapter always fails. Each service and
    session adapter needs an explicit reviewed migration.
13. **Premium media exposure:** returning a directly playable `audioUrl` for
    premium content may bypass future authorization unless URLs are protected or
    signed.
14. **Statistics localization:** backend-returned Nepali display strings are
    difficult to localize and aggregate. Raw numeric metrics would require a
    frontend model change.
15. **Unbounded playlist tracks:** current queue behavior expects every playlist
    track in one response. Large playlists may create performance and playback
    initialization problems.
16. **Local-only mutations:** save, favorite, follow, recent-play, progress, and
    preferences actions currently update Zustand immediately and do not use
    TanStack mutations. Remote synchronization needs optimistic rollback,
    invalidation, offline behavior, and error UX without changing perceived
    responsiveness.

## Recommended implementation boundary

The safest backend-first implementation is to preserve the types above at the
serializer boundary, implement public read endpoints first, and then add
authenticated library/progress endpoints with explicit conflict rules. Remote
frontend adapters should be introduced service-by-service behind the existing
functions. Any move to compact summary serializers, per-group search pagination,
raw statistics, or normalized taxonomy identifiers should be treated as a
versioned contract change and coordinated with the frontend rather than folded
silently into Django implementation.
