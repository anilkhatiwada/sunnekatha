# SunneKatha API Contract

This document defines the expected future Django REST Framework (DRF) boundary.
The frontend still uses mock services. No endpoint in this document is currently
called.

## Integration switch

Environment variables:

```bash
NEXT_PUBLIC_API_MODE=mock
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_API_TIMEOUT_MS=15000
```

`mock` is the safe default. Setting `NEXT_PUBLIC_API_MODE=remote` alone does not
activate network requests; each service must first receive a reviewed remote
adapter. Page components continue importing the same functions from
`src/services`, so switching implementations does not change page code.

## General conventions

- Base path: `/api/v1`
- Media type: `application/json`
- Authentication: `Authorization: Bearer <access-token>`
- Identifiers are opaque strings.
- Detail routes use stable slugs where the frontend exposes human-readable URLs.
- Timestamps use ISO 8601 UTC strings.
- Durations and playback positions use integer seconds.
- JSON field names use the frontend's camelCase contracts. DRF serializers may
  map snake_case model fields using `source=...` or a project-wide renderer.
- List endpoints use DRF page-number pagination unless cursor pagination is
  explicitly documented.

## Response shapes

Page-number pagination:

```json
{
  "count": 42,
  "next": "https://api.example.com/api/v1/tracks/?page=3",
  "previous": "https://api.example.com/api/v1/tracks/?page=1",
  "results": []
}
```

Cursor pagination, recommended for listening history and activity feeds:

```json
{
  "next": "opaque-cursor",
  "previous": null,
  "results": []
}
```

Normalized errors:

```json
{
  "detail": "Human-readable explanation",
  "code": "stable_machine_code",
  "errors": {
    "email": ["Enter a valid email address."]
  }
}
```

The frontend normalizes network, timeout, authentication, permission, not-found,
validation, and server failures into `ApiError`.

## Authentication

JWT endpoints are placeholders:

| Method | Endpoint | Request | Response |
| --- | --- | --- | --- |
| `POST` | `/auth/token/` | `{ email, password }` | `{ access, refresh, user }` |
| `POST` | `/auth/token/refresh/` | `{ refresh }` | `{ access, refresh? }` |
| `POST` | `/auth/logout/` | optional refresh token | `204 No Content` |
| `GET` | `/auth/me/` | — | authenticated user |

The current frontend stores no refresh token. The preferred production design is
an `HttpOnly`, `Secure`, `SameSite` cookie managed by a same-origin backend or
backend-for-frontend. Access-token storage and refresh behavior must be selected
during the authentication milestone. The API client already supports an
injectable access-token provider, one deduplicated refresh attempt after `401`,
and an authentication-failure callback.

## Catalog endpoints

| Method | Endpoint | Query parameters | Response |
| --- | --- | --- | --- |
| `GET` | `/tracks/` | `page`, `pageSize`, `contentType`, `genre`, `mood`, `ordering` | paginated tracks |
| `GET` | `/tracks/trending/` | `limit` | track array |
| `GET` | `/tracks/recent/` | `limit` | track array |
| `GET` | `/tracks/{slug}/` | — | track or `404` |
| `GET` | `/tracks/{id}/similar/` | `limit` | track array |
| `GET` | `/playlists/` | `page`, `pageSize`, `featured`, `mood` | paginated playlists |
| `GET` | `/playlists/featured/` | `limit` | playlist array |
| `GET` | `/playlists/{slug}/` | — | playlist with tracks or `404` |
| `GET` | `/authors/` | `page`, `pageSize`, `ordering` | paginated authors |
| `GET` | `/authors/popular/` | `limit` | author array |
| `GET` | `/authors/{slug}/` | — | author or `404` |
| `GET` | `/authors/{id}/tracks/` | `page`, `pageSize` | paginated tracks |
| `GET` | `/authors/{id}/collections/` | `limit` | playlist array |
| `GET` | `/authors/{id}/related/` | `limit` | author array |
| `GET` | `/narrators/` | `page`, `pageSize`, `ordering` | paginated narrators |
| `GET` | `/narrators/popular/` | `limit` | narrator array |
| `GET` | `/narrators/{slug}/` | — | narrator or `404` |
| `GET` | `/narrators/{id}/tracks/` | `page`, `pageSize` | paginated tracks |
| `GET` | `/narrators/{id}/playlists/` | `limit` | playlist array |
| `GET` | `/genres/` | — | genre array |
| `GET` | `/moods/` | — | mood array |

## Discovery and search

| Method | Endpoint | Query parameters | Response |
| --- | --- | --- | --- |
| `GET` | `/search/` | `q`, `type`, `page`, `pageSize` | grouped search results |
| `GET` | `/search/trending/` | `limit` | string array |
| `GET` | `/home/` | optional locale | composed home payload |

Search must accept Nepali Unicode and Romanized queries. A future backend may
return a composed `/home/` response for fewer round trips; the existing granular
service functions can map sections from that response without changing pages.

## Authenticated library and progress

| Method | Endpoint | Request/Query | Response |
| --- | --- | --- | --- |
| `GET` | `/me/library/` | — | user library |
| `POST` | `/me/favorites/tracks/{trackId}/` | — | `204` |
| `DELETE` | `/me/favorites/tracks/{trackId}/` | — | `204` |
| `POST` | `/me/playlists/{playlistId}/save/` | — | `204` |
| `DELETE` | `/me/playlists/{playlistId}/save/` | — | `204` |
| `POST` | `/me/authors/{authorId}/follow/` | — | `204` |
| `DELETE` | `/me/authors/{authorId}/follow/` | — | `204` |
| `POST` | `/me/narrators/{narratorId}/follow/` | — | `204` |
| `DELETE` | `/me/narrators/{narratorId}/follow/` | — | `204` |
| `GET` | `/me/listening-progress/` | cursor, `pageSize` | cursor-paginated progress |
| `PUT` | `/me/listening-progress/{trackId}/` | `{ progressSeconds, durationSeconds }` | progress |
| `GET` | `/me/listening-statistics/` | optional period | statistics array |
| `GET` | `/me/preferences/` | — | preferences |
| `PATCH` | `/me/preferences/` | partial preferences | preferences |

Progress writes remain throttled by the frontend. The backend should treat
progress updates as idempotent upserts and calculate completion at 90% or more
using the authoritative track duration.

## Migration example

Today a service resolves mock data:

```ts
export async function getTrackBySlug(slug: string): Promise<Track | null> {
  return mockApiResponse(findMockTrack(slug), undefined, null);
}
```

A future adapter can preserve the signature:

```ts
export async function getTrackBySlug(slug: string): Promise<Track | null> {
  try {
    return await apiClient.get<Track>(`/tracks/${encodeURIComponent(slug)}/`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
```

TanStack Query keys are centralized in `src/services/query-keys.ts`, allowing
future mutations to invalidate catalog, detail, library, or profile data without
duplicating array literals.
