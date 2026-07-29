# Backend performance audit

Date: 2026-07-23

## Scope and method

This audit reviewed public catalog, homepage, playlist, search, library, and
listening-progress paths. Query-count tests run with Django's test database
(SQLite); production plans should additionally use PostgreSQL `EXPLAIN
(ANALYZE, BUFFERS)` against representative data.

## Query and serializer findings

| Path | Budget | Notes |
| --- | ---: | --- |
| Homepage, uncached anonymous | 12 | Existing regression test; public sections are cached. |
| Homepage, cached public portion | 0 | Personalized sections are fetched separately and never stored globally. |
| Homepage personalization | 3 | Existing authenticated regression test. |
| Track list | 4 | Count, page, genre prefetch, mood prefetch; independent of page length. |
| Track detail, uncached | 3 | Object plus genre and mood prefetches. Public responses are cached. |
| Playlist list | 3 maximum | Count and annotated page query; track rows are no longer prefetched or nested. |
| Playlist detail, uncached | 4 maximum | Playlist, ordered items/tracks, genres, and moods. Public detail is cached. |
| Saved playlists | 2 | Compact playlist metadata only. |
| Continue listening | 4 | Count, progress/track page, genres, and moods. |
| Progress update | 9 maximum | Includes publication lookup and transactional idempotent upsert. Constant per update. |
| Track search | 6 maximum | Paginated compact results with bounded taxonomy prefetches. |
| Grouped search | 20 maximum | Up to eight independently ranked entity groups; compact payloads prevent nested expansion. |

The principal N+1 risk was playlist serialization: list and grouped-search
responses previously used the detail serializer and embedded every playlist
track. List paths now use `CompactPlaylistSerializer` and skip the item
prefetch. Track collections already use bounded `select_related` and
`prefetch_related` queries. Author, narrator, work, album, and library
collections now use compact serializers as well.

Detail-only text and media metadata are deferred on track, work, album, author,
and narrator collection querysets. List responses do not include transcripts,
waveform arrays, biographies, copyright notes, or long content descriptions.
Detail endpoints retain those fields.

## Search

PostgreSQL search has weighted full-text GIN indexes and trigram GIN indexes for
primary Nepali and English title/name fields. Romanized aliases are normalized
and indexed separately. Grouped search intentionally executes one bounded query
per selected entity type; clients that only need tracks should use the paginated
track-search endpoint or pass a group filter.

Before launch, capture PostgreSQL query plans for common Nepali, English, and
Romanized terms. The broad relationship joins used to match author, genre, mood,
and narrator text can require de-duplication; monitor slow-query logs as catalog
cardinality grows.

## Index review

The important access patterns are covered:

- tracks: publication/featured/date, content type/publication/date,
  narrator/publication/date, work/order, and album/order;
- works and albums: public/featured and content/category access patterns;
- playlists: public listing, featured listing, and owner/type/update order;
- listening and library models: unique relationship constraints plus user and
  recency indexes;
- search: full-text and trigram indexes installed by the PostgreSQL-only search
  migration.

No speculative indexes were added. PostgreSQL should be observed with production
cardinality before adding overlapping indexes, since each index increases write
and vacuum cost.

## Pagination and payload size

Standard page-number pagination defaults to 20 and caps client-selected page
size at 100. Track search and all potentially large public collections use
pagination. Small editorial/taxonomy aggregates remain intentionally bounded by
service limits.

Collection serializers return image URLs, never image bytes. They currently
expose one source image URL rather than thumbnail variants. A future media
pipeline should generate fixed card/detail sizes and serve them through
CloudFront with explicit dimensions to reduce transfer size and layout shift.
Do not introduce synchronous image resizing in API requests.

## Caching

Public homepage data, featured collections, taxonomy lists, public playlist
details, and public track metadata use namespaced cache keys and explicit
invalidation. Default durations are:

- homepage, featured collections, and public details: 300 seconds;
- taxonomy lists: 900 seconds.

Favorites, continue listening, private playlists, queues, and authentication
responses are not globally cached. Personalized homepage data is composed after
the shared public cache lookup.

## Remaining risks and follow-up

- Query-count tests prevent N+1 regressions but do not measure latency, buffer
  reads, Redis round trips, or serialized byte size.
- Grouped search is the most query-intensive endpoint by design. Prefer
  type-specific search for infinite scrolling and add endpoint-level timing
  metrics before changing its architecture.
- Offset pagination performs a count query and degrades at very deep pages.
  Cursor pagination is already available and should be considered for very large
  chronological track/history feeds.
- Add production observability for p95 latency, SQL duration, response bytes,
  cache hit rate, and slow queries. Revisit budgets using representative
  PostgreSQL data before launch.
