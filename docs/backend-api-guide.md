# SunneKatha Backend API Guide

## Contract and documentation

The API base path is `/api/v1`. JSON field names follow the existing frontend
contract and are camelCase. IDs are UUID strings, detail routes generally use
slugs, dates are ISO 8601 strings, and playback durations and positions are
seconds.

Interactive and machine-readable documentation is available at:

- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`
- ReDoc: `GET /api/redoc/`

The schema is the source of truth for individual fields, enum values, filters,
and response components. This guide covers frontend orchestration and state
ownership.

## Next.js API client

Keep all requests behind `src/services/`. Configure the API origin with a
server-only or `NEXT_PUBLIC_` environment variable as appropriate for where the
request runs. Do not embed refresh tokens, AWS credentials, S3 keys, or
CloudFront signing material in the frontend.

```ts
type ApiError = {
  detail: string;
  code: string;
  errors?: Record<string, string[]>;
};

type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(accessToken
        ? { Authorization: `Bearer ${accessToken}` }
        : {}),
      ...init.headers,
    },
  });

  if (response.status === 204) return undefined as T;
  const data = await response.json();
  if (!response.ok) throw data as ApiError;
  return data as T;
}
```

Use TanStack Query for server data. Include every filter and pagination value in
the query key, for example `["tracks", { genre, language, ordering, page }]`.
Do not copy query results into Zustand. Zustand remains appropriate for the
immediate audio element, local queue transitions, and other truly client-owned
state.

## Authentication

Register with `POST /api/v1/auth/register/` or log in with
`POST /api/v1/auth/login/`:

```json
{
  "email": "srota@example.com",
  "password": "StrongPass!234"
}
```

Both flows return an access token, refresh token, and current user. Send the
access token as:

```http
Authorization: Bearer eyJ...
```

Access tokens are short-lived. Refresh with
`POST /api/v1/auth/token/refresh/`:

```json
{ "refresh": "eyJ..." }
```

Refresh rotation is enabled. Replace the stored refresh token whenever the
response contains a new one; the previous token is blacklisted. Logout with
`POST /api/v1/auth/logout/` and the current refresh token in the body.

For a browser application, prefer keeping refresh credentials in a secure
server-managed session or HTTP-only cookie layer. If the frontend stores tokens
directly, never use persistent browser storage for long-lived refresh tokens.
On a single `401`, perform one coordinated refresh and retry pending requests
once. Do not create refresh loops.

## Pagination, filters, and ordering

Standard lists use:

```json
{
  "count": 42,
  "next": "https://api.example.com/api/v1/tracks/?page=2",
  "previous": null,
  "results": []
}
```

Use `page` and `pageSize`; the default size is 20 and maximum is 100. Treat
`next` and `previous` as opaque URLs.

Track filters include `contentType`, `author`, `narrator`, `genre`, `mood`,
`language`, `featured`, `premium`, and `explicit`. The Explore track API also
accepts `content_type` for compatibility. Search and ordering parameters are
documented per operation in OpenAPI. Send slug values for taxonomy and people
filters unless the schema states otherwise.

```http
GET /api/v1/tracks/?genre=katha&language=ne&premium=false&ordering=-published_at
```

Public catalog endpoints only return published content. Do not attempt to hide
premium or explicit records exclusively in the UI; backend permissions and user
preferences remain authoritative.

## Error handling

Every handled API error uses:

```json
{
  "detail": "Validation failed.",
  "code": "validation_error",
  "errors": {
    "progressSeconds": [
      "Ensure this value is greater than or equal to 0."
    ]
  }
}
```

Use `code` for program behavior, `detail` for a general message, and `errors`
for field-level form feedback. Expected statuses include:

- `400`: invalid input or state transition
- `401`: missing, expired, or invalid authentication
- `403`: authenticated but not entitled or permitted
- `404`: absent resource or a resource intentionally hidden by ownership rules
- `429`: throttled; respect `Retry-After` when present
- `500`: safe generic server error

Do not infer that a hidden private or unpublished object exists from a `404`.

## Direct upload flow

Uploads are available only to authenticated creators or staff.

1. Request a session with `POST /api/v1/uploads/`.
2. Submit the file directly to the returned S3 `upload.url`, including every
   returned form field exactly as supplied.
3. Confirm with `POST /api/v1/uploads/{sessionId}/confirm/`.
4. Poll `GET /api/v1/uploads/{sessionId}/` only when the UI needs status.
5. Cancel unused sessions with
   `POST /api/v1/uploads/{sessionId}/cancel/`.

```json
{
  "uploadType": "audio_master",
  "originalFilename": "katha.mp3",
  "contentType": "audio/mpeg",
  "expectedSize": 8451200
}
```

The server validates type and size and creates the object key. The frontend must
never construct, modify, or reuse `objectKey`. A presigned response resembles:

```json
{
  "id": "6f37bcd4-412d-44b6-b335-9c2c2d506a19",
  "status": "pending",
  "expiresAt": "2026-07-23T17:15:00Z",
  "upload": {
    "url": "https://private-bucket.s3.amazonaws.com/",
    "fields": {
      "key": "temporary/uploads/audio-master/..."
    }
  }
}
```

Use `FormData` for the S3 POST and append the file after the supplied fields.
The S3 request does not use the SunneKatha JWT. Confirmation verifies the object
before changing server state. Upload processing completion or failure appears
through the in-app notifications API; there is no email or push delivery yet.

## Audio stream and premium authorization

Fetch display/player metadata first, then request media authorization immediately
before playback:

```http
GET /api/v1/tracks/{slug}/stream/?quality=auto&includeIntroduction=false
```

The response contains the selected `quality`, a CloudFront `url`, optional
`expiresAt`, compact track metadata, authorization information, and an optional
`introduction` object:

```json
{
  "quality": "high",
  "url": "https://media.example.com/opaque/audio.m4a?Policy=...",
  "expiresAt": "2026-07-23T17:05:00Z",
  "introduction": null,
  "authorization": {
    "status": "authorized",
    "accessType": "premium",
    "isEntitled": true,
    "isPrivileged": false
  }
}
```

Set `includeIntroduction=true` only when a track is reached through a playlist,
queue, play-all action, or automatic transition. When the track has an enabled
spoken introduction, the response includes its protected `url`, `expiresAt`, and
duration. Direct/manual track playback must leave this parameter false so the
main literary audio begins immediately. If the introduction cannot be loaded,
the player should continue with the main track. Listening progress, completion,
history duration, and play counts apply only to the main track.

Free published tracks work anonymously. Premium tracks require a valid
subscription or content entitlement. Unpublished content is limited to
authorized staff or creators. A visible premium card does not imply access.

Signed URLs are short-lived capabilities. Keep them only in player memory, do
not place them in durable Zustand persistence or TanStack Query persistence, do
not log them, and do not expose them in analytics. When a URL expires, request a
new stream authorization and resume at the current player position. Django
never serves the audio bytes.

## Listening progress

Progress is one idempotently updated record per user and track:

```http
PUT /api/v1/me/listening-progress/{trackId}/
Content-Type: application/json

{
  "progressSeconds": 315.25,
  "durationSeconds": 842
}
```

Send updates every 15–30 seconds, on pause, track change, and before leaving
when practical. Do not send per-second events. Negative values and significant
duration overshoots are rejected. Progress at 90% or above is completed.

Use:

- `GET /api/v1/me/listening-progress/{trackId}/` to restore one track
- `GET /api/v1/me/continue-listening/` for the ordered rail
- `POST /api/v1/me/listening-progress/{trackId}/complete/` on a completed event
- `DELETE /api/v1/me/listening-progress/{trackId}/remove/` to dismiss an item

Keep raw playback sessions separate from progress. Session analytics record
meaningful transitions and cumulative listened time, not player ticks.

## Queue synchronization

The browser player is the immediate source of truth. The server queue is a
cross-device restoration snapshot.

Fetch `GET /api/v1/me/queue/` after authentication/hydration. Replace the queue
transactionally:

```http
PUT /api/v1/me/queue/

{
  "trackIds": [
    "f60f09ad-7bc5-4cf0-8368-b199aa076d59",
    "20c1641a-585a-4a71-8b66-1996e702f41b"
  ],
  "currentIndex": 0,
  "positionSeconds": 315.25
}
```

Duplicate track IDs are valid and become different queue items. Use queue item
IDs—not track IDs—for removal and reordering. Reordering must submit every
current item exactly once:

```json
{
  "itemIds": [
    "e24195ab-273e-47c2-8d3c-3e91c3664344",
    "05458955-e05b-43e3-bc09-20128eb034c0"
  ]
}
```

Other operations are:

- `POST /api/v1/me/queue/items/` with `trackId`
- `POST /api/v1/me/queue/play-next/` with `trackId`
- `DELETE /api/v1/me/queue/items/{queueItemId}/`
- `PATCH /api/v1/me/queue/reorder/` with all ordered `itemIds`
- `PATCH /api/v1/me/queue/position/` with `currentIndex` and `positionSeconds`
- `PATCH /api/v1/me/queue/shuffle/` with `isShuffleEnabled`
- `PATCH /api/v1/me/queue/repeat/` with `repeatMode`
- `DELETE /api/v1/me/queue/` to clear

Debounce restoration-position writes and send them on meaningful player
transitions. Serialize queue mutations or invalidate/refetch the queue after a
mutation to prevent an older response from overwriting newer client state.

## Frontend cache and privacy rules

Public catalog queries may use normal TanStack Query caching. Query keys for
user data must include an authenticated-user boundary, and all user-specific
queries must be cleared on logout:

- current user and notifications
- favorites and followed entities
- private playlists
- continue listening and listening history
- queue and playback sessions

Never globally cache or statically render personalized API responses. Server
components that forward a bearer token should use request-scoped fetching and
`cache: "no-store"`. Do not expose private playlist IDs, signed stream URLs,
tokens, or upload object keys through logs, telemetry, or shared caches.
