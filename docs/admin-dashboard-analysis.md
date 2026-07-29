# SunneKatha Admin Dashboard Analysis

## Scope and baseline

This is a read-only assessment of the existing Django backend as of 2026-07-24.
It proposes an admin-dashboard implementation order but does not install Django
Unfold or change application code.

- Django is pinned to `>=5.2,<5.3`; the inspected environment reports Django
  **5.2.16**.
- Settings are split into `base`, `local`, `production`, `build`, `test`, and
  `ci`. `base` defines shared applications, REST, storage, cache, Celery, and
  template/static settings. Production adds required environment validation,
  WhiteNoise, HTTPS/cookie/HSTS policy, proxy handling, JSON logging, and stricter
  Celery behavior.
- The project uses Django's global `admin.site` at `/admin/`. There is no custom
  `AdminSite`, custom admin index, dashboard context provider, or admin URL
  namespace.
- Installed project applications are `accounts`, `analytics`, `authors`,
  `catalog`, `common`, `creators`, `explore`, `home`, `library`, `media_access`,
  `narrators`, `notifications`, `playlists`, `search`, `subscriptions`,
  `taxonomy`, and `uploads`. Third-party applications are CORS headers,
  django-filter, drf-spectacular, DRF, Simple JWT with blacklist support,
  and django-storages.
- The custom `accounts.User` extends `AbstractUser` and the reusable UUID
  timestamp model. Email is the login identifier. It retains Django groups,
  per-model permissions, `is_staff`, and `is_superuser`, and adds profile,
  playback-preference, and `is_creator` fields.
- All 38 project persistence models discovered through Django's app registry are
  currently registered in the admin.
- `TEMPLATES` uses `APP_DIRS=True`, no project template directories, and the
  standard request/auth/messages context processors. No project-owned admin
  templates were found. Static files use Django's normal storage outside
  production and WhiteNoise's compressed manifest storage in production;
  `STATIC_ROOT` is `backend/staticfiles`. No project static source directory was
  found.

## 1. Existing admin registrations

| Area | Registered models | Current admin behavior |
| --- | --- | --- |
| Accounts | User | Extends `UserAdmin`; email/display search, status and preference filters, avatar preview, grouped identity/preferences/permissions fields, protected deletion. |
| People | Author, Narrator | Bilingual search, featured/verified filters, image preview, immutable UUID/slug/timestamps, autocomplete for a narrator's linked user, and feature/unfeature actions through `EditorialService`. |
| Catalog | LiteraryWork, Album, AudioTrack | Shared publication/featured actions, bilingual search, taxonomy filters, relation autocomplete, cover preview, protected deletion, and optimized relation loading. Albums have a read-only track inline. Tracks show formatted duration and processing status, and expose publish/review/retry/featured actions through `EditorialService`. |
| Editorial home | HomeSection, HomeSectionItem | Section scheduling and ordering fields, item inline, polymorphic target autocomplete, target summary, and immutable section type after creation. Sections are protected from deletion; separately registered items are not. |
| Playlists | Playlist, PlaylistItem | Owner-aware search, type/visibility/publication filters, cover preview, ordered item inline, publication and featured actions through `EditorialService`, and protected deletion. |
| Taxonomy | Genre, Mood, Language, ContentCategory | One shared admin with bilingual search, image preview, active filter, editable sort order/active state, and protected deletion. |
| Creators and rights | CreatorProfile, ContentContributor, RightsLicenseAudit | Basic creator approval/role and contributor management. Rights/license audits are immutable and searchable. |
| Listener library | FavoriteTrack, SavedPlaylist, FollowedAuthor, FollowedNarrator, ListeningProgress, PlaybackSession, ListeningHistory, PlaybackEvent, UserQueue, UserQueueItem | Relationships have search/autocomplete. Playback, history, progress, events, queues, and queue items are largely read-only; sessions include event inlines and queues include item inlines. Relationship records are still directly editable/deletable. |
| Analytics | DailyPlatformMetric, DailyTrackMetric, DailyAuthorMetric, DailyNarratorMetric, DailyPlaylistMetric | Read-only generated metrics, no add permission, protected deletion, date filters, entity search, and optimized related-object loading. |
| Subscriptions | SubscriptionPlan, UserSubscription, ContentEntitlement | Plan/access filters and autocomplete; protected deletion. User subscriptions have staff-grant and revoke actions. Entitlements are directly editable. |
| Uploads | UploadSession | Status/type filters, user/file/key search, formatted size/expiry metadata, read-only fields, no deletion. |
| Notifications | Notification | Type/read/date filters and recipient/content search. Records are read-only, cannot be added, and cannot be deleted. |
| Search | SearchAlias | Entity filter, alias/object search, normalized alias and timestamps read-only. |

`common`, `explore`, and `media_access` have no persistence models requiring
registration. `common.admin` supplies reusable protected-deletion and image/cover
preview mixins.

## 2. Models requiring improved admin pages

### Highest priority

- **AudioTrack** needs a review-focused change form: clear draft/submitted/
  approved/rejected and pending/processing/ready/failed state, rights summary,
  contributor ownership, safe workflow buttons, media availability, and direct
  links to related work, album, narrator, upload, and analytics records.
- **LiteraryWork and Album** need compact editorial fieldsets, rights visibility,
  publication readiness indicators, content previews, and useful related-track
  navigation. Long bilingual descriptions should not dominate list pages.
- **Playlist and PlaylistItem** need service-backed ordering controls. The current
  editable inline can bypass `PlaylistItemService`, including its locking,
  position normalization, duplicate protection, and update notification.
- **HomeSection and HomeSectionItem** need ergonomic drag/order controls and
  validation feedback for their exactly-one-target rule and scheduled-active
  state.
- **UploadSession** needs an operational status view with expiry, object
  verification outcome, uploader, and links to any later processing record.
  Object keys must remain read-only and should be visually de-emphasized.
- **CreatorProfile, ContentContributor, and RightsLicenseAudit** need an approval
  queue, readable role display, ownership context, and an auditable rights panel.

### Operational and support priority

- **User, UserSubscription, SubscriptionPlan, and ContentEntitlement** need
  explicit staff-only operational controls and a combined access summary.
  Entitlement/subscription changes should not be ordinary free-form edits.
- **PlaybackSession, ListeningProgress, ListeningHistory, PlaybackEvent,
  UserQueue, and UserQueueItem** should be clearly diagnostic/read-only for most
  staff. These records are user state or analytics input, not editorial content.
- **Daily metric models** need dashboard summaries, date-range navigation, and
  links to source entities. Their existing immutable list/detail pages are a
  sound base.
- **Author, Narrator, taxonomy models, and SearchAlias** mainly need presentation
  improvements, cross-links, count annotations, and consistent bilingual
  fieldsets.
- **Favorite/follow/save relationships and Notification** should be treated as
  support/audit data. Direct mutation should be restricted unless a documented
  support workflow requires it.

## 3. Existing services that admin actions should call

| Service | Admin-safe responsibilities | Integration note |
| --- | --- | --- |
| `apps.catalog.services.EditorialService` | Publish/unpublish works, albums, playlists, and eligible tracks; approve/reject reviewed tracks; retry failed processing state; feature/unfeature supported content; notification and cache invalidation. | Existing catalog, author, narrator, and playlist actions already use it. New buttons must continue to do so and surface partial/skipped results. |
| `apps.playlists.services.PlaylistItemService` | Add/remove/reorder items transactionally, lock the playlist, preserve stable positions, reject duplicates, and notify playlist followers. | Current admin inline does not use it. An improved ordering UI must call this boundary instead of direct inline writes. |
| `apps.uploads.services.UploadSessionService` | Validate upload request, generate server-controlled S3 key and presigned POST, verify object metadata/signature on confirmation, expire/cancel sessions, and delete canceled pending objects. | The admin should inspect status and invoke only explicit service methods; it must never allow object-key editing or manufacture upload sessions outside the service. |
| `apps.analytics.services.DailyAnalyticsAggregationService` | Rebuild daily platform/entity aggregates transactionally from playback sessions. | Suitable for a narrowly scoped staff action or task trigger, not synchronous aggregation while rendering a dashboard. |
| `apps.media_access.services.CloudFrontMediaService` | Authorize free, premium, creator, and staff stream access; select quality; produce stable or short-lived signed CloudFront URLs. | Admin preview links must use this service. Never render raw S3 names as clickable URLs or persist signed URLs. |
| `apps.notifications.services.NotificationService` | Produce deduplicated workflow notifications. | Prefer indirect use through publishing/playlist services; dashboard actions should not duplicate notifications themselves. |
| Library services (`ListeningProgressService`, `PlaybackSessionService`, `UserQueueService`) | Validate and synchronize listener progress, sessions/history/events, and queue state. | Admin pages should normally remain diagnostic. Any support repair must call these services rather than editing state tables directly. |

The current subscription grant/revoke admin actions implement transaction and
status updates inside `UserSubscriptionAdmin`; no subscription management service
exists. Before expanding these controls, extract or introduce a narrow service so
API/admin behavior, validation, auditability, and cache invalidation cannot
diverge.

## 4. Existing permission roles

- **Superuser** receives Django's full admin authority.
- **Staff** can enter the stock admin when active and then relies on Django model
  permissions. API services also treat active staff as editorial/privileged
  actors. There is no custom editor-only `AdminSite` or object-level admin
  permission layer.
- **Creator** is an active user with `is_creator=True`. A `CreatorProfile` can
  carry `narrator`, `editor`, `uploader`, and `rights_holder` roles plus
  `is_approved`. The API's broad entry permission accepts `is_creator` or staff;
  more specific ownership checks then constrain tracks.
- **Track owner/contributor** is derived from a narrator linked to the user or a
  `ContentContributor`. Creators can manage only unpublished owned tracks.
- **Rights holder** is a track contributor with the `rights_holder` role. Rights
  changes are allowed to staff or that contributor and create a
  `RightsLicenseAudit`.
- **Playlist owner** can manage only their own user playlist. Active staff can
  manage non-user/editorial playlists. Private visibility is enforced in API
  querysets, not by a special admin role.
- **Premium listener** is determined by active/trial/staff-granted subscription
  state or a current per-track entitlement. Staff is treated as premium for
  access helpers.

Unfold must not be treated as a permission system. Navigation visibility,
dashboard cards, custom views, actions, and object queries must call Django
permission checks and existing ownership/service rules. In particular,
`is_creator` alone must not grant admin access; `is_staff` and appropriate model
permissions remain required.

## 5. Existing publishing workflow

1. A creator edits an **unpublished owned draft**. Published fields are protected
   by the creator serializers.
2. Rights fields on the related literary work require staff or a rights-holder
   contribution. Effective changes create an immutable `RightsLicenseAudit`.
3. Submission is allowed from draft/rejected state only when audio processing is
   `ready`; the track becomes `submitted`.
4. Staff may reject a submitted track or approve and publish it. Approval requires
   both `submitted` review state and `ready` processing state and records reviewer
   metadata.
5. Publication sets the required publication timestamp/status, notifies relevant
   followers/creators, and invalidates applicable public caches.
6. Unpublish and feature/unfeature operations also run through
   `EditorialService`. A playlist may be featured only when editorial.

Database constraints back important states, including a publication timestamp for
published works/tracks and ready processing for published tracks. Admin controls
should present transitions, not unrestricted booleans, and show why an ineligible
record was skipped.

## 6. Existing audio-processing workflow

There is **no implemented audio transcoding or waveform-processing service and no
audio Celery task**. The model has:

- master, high-quality, and low-quality file fields;
- `pending`, `processing`, `ready`, and `failed` processing states;
- waveform/transcript fields and review metadata.

The existing “retry processing” service/admin action only changes a failed track
back to `pending`. It does not enqueue work. The only discovered Celery task is
daily analytics aggregation. Therefore an admin dashboard may display processing
state and offer the existing reset action, but must not label it as a completed
retry pipeline until a real idempotent processing task, failure metadata, and
queueing service exist.

## 7. Existing upload workflow

1. An authenticated creator or staff user requests an upload session for an audio
   master, cover, narrator image, or author image.
2. The service validates extension, MIME type, expected size, and configured
   limits. It strips the presented filename and generates a UUID-based,
   server-controlled key under `temporary/uploads/...`.
3. S3 returns a short-lived presigned POST constrained by exact key/type,
   encryption, and a bounded size range.
4. Confirmation locks the session, handles expiry/idempotency, verifies the object
   exists, checks exact length/content type/AES-256 metadata, and verifies leading
   file signature bytes before marking it confirmed.
5. Cancellation is transactional and removes a pending object where possible.

S3 classes keep originals, processed audio, and temporary uploads private; cover
objects remain private at S3 but can use a CloudFront custom domain. Development
uses local filesystem fallbacks. Upload confirmation currently does not promote
the temporary object, create a track, or enqueue processing. An admin UI must not
bridge this gap with direct file/object-key edits.

CloudFront remains the media delivery boundary: public free tracks may receive a
stable URL, while premium or unpublished authorized tracks receive short-lived
signed URLs. Django does not proxy audio bytes. Admin previews must preserve that
design.

## 8. Existing analytics data

Daily aggregate tables exist for:

- the platform;
- tracks;
- authors;
- narrators;
- playlists.

Each stores date, total plays, unique listeners, listening seconds, and completed
plays; entity tables add popularity-oriented indexes. A Celery Beat job runs at
02:15 UTC and invokes `aggregate_daily_analytics` for the previous day. The task
retries database errors with backoff/jitter up to three times. Aggregation replaces
the day's entity rows inside a transaction and reads `PlaybackSession`, avoiding
expensive live aggregation for the staff analytics API. Staff-only API access and
a minimum-listener privacy setting already exist.

Dashboard charts should query these daily tables, enforce the configured date
range/privacy threshold, and cache only non-sensitive aggregates. They should not
aggregate raw playback rows during page rendering. Playlist metrics currently
attribute a session to every published playlist containing its track rather than
to a captured playback-origin playlist; dashboard copy must not imply stronger
attribution.

## 9. Risks of adding Django Unfold

1. **Django 5.2 compatibility:** select an Unfold release that explicitly supports
   Django 5.2 and verify the Python version matrix. No Unfold dependency is
   currently installed.
2. **Template replacement:** Unfold overrides admin templates. The project
   currently depends only on Django app templates, so navigation, login,
   change-form, action-confirmation, autocomplete, inline, and message rendering
   all require regression testing.
3. **Static production behavior:** Unfold assets must survive
   `collectstatic` with `CompressedManifestStaticFilesStorage`, hashed-file
   cleanup, WhiteNoise, and CSP/proxy deployment assumptions.
4. **Registration/order changes:** Unfold must precede `django.contrib.admin` as
   required by its integration. Reordering applications can alter template
   resolution and must be isolated to settings.
5. **False security from hidden UI:** hiding modules, buttons, or dashboard cards
   is not authorization. Every custom view and action needs server-side model and
   object permission checks.
6. **Service bypass:** richer inlines, bulk editors, and custom buttons can write
   models directly, bypassing transactions, cache invalidation, notifications,
   review rules, playlist ordering, rights audits, and media security.
7. **Bulk-action ambiguity:** current services can skip ineligible records.
   Unfold action feedback must report updated/skipped counts and avoid implying
   atomic success across an arbitrary selection.
8. **Media leakage:** image preview mixins call storage URLs, and audio fields
   contain private object names. Custom displays must not expose raw S3 paths,
   long-lived audio links, signer material, or upload keys as public links.
9. **Long/large fields:** transcripts, descriptions, waveform JSON, rights
   changes, and analytics data can make change pages slow or huge. Use collapsed
   sections, summaries, pagination, and deferred fields where appropriate.
10. **Query regressions:** dashboard counts and badges can introduce N+1 queries
    or repeated full-table counts. Precompute/annotate deliberately and add
    query-count tests.
11. **Localization/accessibility:** bilingual Nepali/English forms require
    appropriate fonts, line heights, ordering, keyboard focus, contrast, and
    mobile behavior; a visual theme alone does not guarantee these.
12. **Upgrade surface:** custom Unfold components and template overrides create a
    maintenance dependency. Prefer configuration and standard `ModelAdmin`
    extension points before copying templates.
13. **Test environment mismatch:** most unit tests use test settings and cheap
    backends, while production uses PostgreSQL, Redis, S3/CloudFront, and
    manifest static files. A production-like admin smoke test is needed.

The existing test suite contains 58 `test_*.py` modules across the backend,
including admin behavior for catalog, taxonomy, and home, plus service/API/model
coverage. It has no custom-site or Unfold-specific UI/static regression suite.

## 10. Proposed implementation order

1. **Establish a safety baseline.** Record current admin URLs/registrations,
   Django checks, migration state, selected admin permission behavior, query
   counts, and production `collectstatic`. Add tests before changing templates.
2. **Choose and validate Unfold in isolation.** Confirm Django/Python support,
   add it only to requirements and installed-app ordering, and reproduce the
   stock admin behavior without custom dashboards.
3. **Define admin information architecture.** Group Editorial, People,
   Taxonomy, Creators & Rights, Audience, Commerce, Operations, and Analytics.
   Apply navigation permission callbacks based on Django model permissions.
4. **Create reusable presentation primitives.** Add safe status badges, bilingual
   fieldsets, related-object links, compact image previews, duration/size
   formatting, and protected action feedback. Do not add business logic here.
5. **Upgrade the editorial core.** Implement workflow-oriented pages for tracks,
   works, albums, authors, narrators, and taxonomy. Keep all publication,
   review, retry-state, featured, notification, and invalidation behavior inside
   `EditorialService`.
6. **Fix ordered-content mutation.** Replace direct playlist item mutation with
   `PlaylistItemService`; then improve playlist and home-section ordering while
   preserving validation and stable positions.
7. **Add creator/rights/upload operations.** Present creator approval,
   contributors, immutable rights audits, and upload status. Keep object keys and
   storage details read-only and do not invent a processing pipeline.
8. **Harden subscription and support operations.** Extract subscription
   grant/revoke logic into a service with an audit trail, then expose narrowly
   permissioned actions. Make listener state and notifications explicitly
   diagnostic/read-only unless a support repair service is designed.
9. **Add the analytics dashboard.** Read daily aggregates only, enforce staff
   permissions/privacy thresholds/date bounds, and avoid raw per-user data or
   synchronous aggregation.
10. **Production validation and rollout.** Run checks, migration checks, complete
    tests, admin permission tests, query-count tests, accessibility smoke tests,
    `collectstatic`, and a production-container smoke test. Roll back by removing
    Unfold configuration while retaining standard `ModelAdmin` registrations;
    avoid irreversible data migrations in the initial adoption.
