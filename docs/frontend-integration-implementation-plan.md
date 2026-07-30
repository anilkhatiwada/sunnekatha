# SunneKatha frontend completion plan

**Date:** 2026-07-30

**Status:** Implemented and reviewed

## Objective

Complete the existing Next.js product by connecting every in-scope user-facing
feature to the existing Django REST API while preserving the current visual
language, routes, accessibility, and local-first playback behavior.

## Non-goals

- Rebuilding the frontend or backend.
- Exposing staff-only Admin workflows in the public application.
- Replacing Django contracts without a documented incompatibility.
- Persisting signed media URLs or exposing S3 object keys.
- Making mock data an automatic production fallback.

## Confirmed architecture

- TanStack Query owns remote and personalized server state.
- Zustand remains the immediate source of truth for active playback and a
  network-failure fallback for progress and queue state.
- Django remains authoritative for authenticated library relationships,
  playlists, progress, history, queue restoration, notifications, creator
  metadata, and upload sessions.
- Track metadata and stream authorization remain separate. A signed or stable
  media URL is requested only on playback intent and refreshed when needed.
- Production requests use `https://api.sunnekatha.com/api/v1`.

## Design findings

1. Logged-out navigation now correctly omits Library and Profile.
2. Personalized actions now show an explicit sign-in prompt for anonymous
   visitors.
3. The Library page currently resolves saved IDs against a complete mock
   catalog. Production must render the paginated compact objects returned by
   the authenticated list endpoints instead.
4. Compact playlists now hydrate detail only after playback intent.
5. Remote collection playback preserves the ordered queue and refreshes an
   expired current media URL once.
6. Email/password registration, password change, notifications, and creator
   tools now have frontend surfaces.
7. Literary works, albums, genre pages, and mood pages now have dedicated
   routes.
8. Mutation feedback and protected error states use existing shared UI
   patterns.

## Implementation order

1. Authenticated library queries and idempotent optimistic relationship
   mutations.
2. Server progress, continue listening, recently played, and playback sessions.
3. Server queue restoration and debounced synchronization with lazy stream
   authorization.
4. User playlist CRUD, track management, visibility, and duplication.
5. Missing catalog routes, filters, pagination, and notifications.
6. Account registration/password management.
7. Creator profile, direct-to-S3 upload, draft metadata, processing status, and
   review submission.
8. Mock dependency removal, responsive/accessibility audit, end-to-end contract
   validation, and production deployment.

## Key risks and rollback

- A stale server queue must never overwrite an active local playback session.
- Progress and analytics failures must never stop audio playback.
- Optimistic relationship mutations must roll back on permission or network
  errors.
- Premium URLs must not be stored in persisted Zustand state.
- Direct uploads remain unavailable unless S3 CORS explicitly permits
  `https://sunnekatha.com`.
- Each integration area is committed independently so the live frontend can
  roll back to the previous immutable release.

## Engineer handoff

Implement the ordered phases above using the existing `apiClient`, mapper
functions, query-key families, cards, player controls, and error components.
Add contract-focused tests before replacing each mock consumer. Do not delete
mock files until repository search confirms no production consumer remains.
