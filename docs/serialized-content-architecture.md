# Serialized Content Architecture

SunneKatha represents playback and discovery separately:

- `AudioTrack` remains the playback identity used by streaming, progress,
  history, favorites, analytics, queues, introductions, and advertisements.
- A standalone work is discovered through its published track, as before.
- A serialized `LiteraryWork` is the discovery identity. Its published, ready
  tracks are ordered chapters and are not returned by general track feeds.

## Data model

- `LiteraryWork.structure`: `standalone` or `serialized`.
- `LiteraryWork.category`: retained as the primary category for compatibility.
- `LiteraryWork.categories`: additional browse categories. API responses always
  include the primary category in the `categories` array.
- `LiteraryWork.tags`: extensible discovery and recommendation metadata.
- `AudioTrack.chapter_number`: required for tracks under serialized works and
  unique within a work.
- `AudioTrack.cover_image`: optional; clients fall back to album or work artwork.
- `PlaylistItem`: contains exactly one track or serialized work. Playlist API
  `items` preserves this presentation while legacy `tracks` expands works into
  the ordered playback queue.
- `HomeSectionItem`: may reference a work in work, mixed-catalog, or hero
  sections.

## API behavior

- `GET /api/v1/catalog/items/` returns a paginated discriminated union:
  `{kind: "track"|"work", content: ...}`. It accepts category, tag, genre,
  mood, author, narrator, language, premium, and explicit filters.
- `GET /api/v1/works/{slug}/` embeds ordered published chapters.
- `GET /api/v1/tracks/` excludes serialized chapters unless `work=<slug>` is
  explicitly supplied. Direct track detail and stream URLs remain valid.
- Playlist detail returns both presentation `items` and an expanded `tracks`
  queue for backward-compatible playback.
- `POST /api/v1/playlists/{slug}/works/add/` and `/works/remove/` manage
  serialized parent items.
- `GET /api/v1/tags/` exposes active tags.

## Editorial rules

Serialized chapters require unique positive chapter numbers. A serialized work
is publicly discoverable only when the parent is published and it has at least
one published, processing-ready chapter. General homepage, explore, search, and
related-track queries suppress serialized chapters; editors select the parent
work instead.

## Migration and rollback

The data migration copies every legacy primary category into the new many-to-many
category relation and stops if duplicate chapter numbers already exist. Existing
works default to `standalone`, so current URLs and playback records retain their
meaning. Rollback should be performed by restoring the pre-migration database;
removing the new relations after editors begin using them would discard metadata.
