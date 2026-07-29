# SunneKatha Admin Dashboard: Production-Readiness Report

Audit date: 2026-07-29
Runtime reviewed: Django 5.2.16, Django Unfold 0.101.0

This report covers the existing Django administration application. The audit
included configuration and code inspection, permission and workflow tests,
static-file validation, the complete automated test suite, and live responsive
checks at 768, 1024, 1280, and 1440 pixels.

## 1. Features implemented

- Branded Django Unfold administration with SunneKatha title, header, subtitle,
  monogram, favicon, environment label, dark-first palette, and compatible light
  mode.
- Permission-aware, collapsible navigation for content, editorial, taxonomy,
  audio operations, rights, audience, and system administration.
- A compact operational dashboard containing content, processing, account,
  subscription, review, and listening metrics plus attention queues and recent
  activity.
- Focused administration experiences for authors, narrators, literary works,
  albums, audio tracks, playlists, homepage sections, upload sessions,
  copyright records, users, subscriptions, and analytics.
- Consistent status badges, date/range filters, relationship autocomplete,
  thumbnails, safe previews, compact tables, and human-readable durations and
  file sizes.
- Editorial review, scheduled publication, processing retry, ordered playlist,
  ordered homepage, rights verification, subscription intervention, metadata
  transfer, and administrative audit workflows.
- Accessible labels for operational search/filter forms and contextual action
  labels. Custom dashboard pages retain one page-level heading.
- Tablet and smaller-laptop layouts with responsive cards, wrapping actions,
  scroll-safe tables and inlines, long-title handling, and keyboard-compatible
  ordering controls.

## 2. Admin URLs

The existing admin root and authentication remain unchanged:

| Purpose | URL |
| --- | --- |
| Dashboard | `/admin/` |
| Login | `/admin/login/` |
| Logout | `/admin/logout/` |
| Password change | `/admin/password_change/` |
| Model lists | `/admin/<app-label>/<model-name>/` |
| Model add | `/admin/<app-label>/<model-name>/add/` |
| Model change | `/admin/<app-label>/<model-name>/<object-id>/change/` |
| Failed processing | `/admin/catalog/audioprocessingjob/failed/` |
| Retry one processing job | `/admin/catalog/audioprocessingjob/failed/<job-id>/retry/` |
| Scheduled publications | `/admin/catalog/audiotrack/scheduled-publications/` |
| Pending reviews | `/admin/catalog/pendingreviewtrack/` |
| Listening analytics | `/admin/analytics/dailyplatformmetric/dashboard/` |
| Analytics CSV | `/admin/analytics/dailyplatformmetric/dashboard/export.csv` |
| Metadata transfer | `/admin/metadata-transfer/` |

Secure audio-preview and permission-document routes are generated through named
admin URL reversals. They are deliberately object-specific, permission checked,
and omitted here as shareable links because their responses may contain
short-lived access data.

## 3. Roles and permissions

Run `python manage.py setup_staff_roles` to create or update the additive role
matrix. The command does not remove independently assigned custom permissions.

| Role | Intended authority |
| --- | --- |
| Super Administrator | All defined administrative capabilities, system administration, and explicitly authorized self-review |
| Publisher | Edit and review content, publish, manage playlists/homepage, view rights |
| Senior Editor | Edit and review content, manage playlists/homepage, view rights |
| Editor | Edit content and homepage, view rights; cannot approve or publish |
| Audio Manager | View content, manage uploads/audio, retry processing |
| Playlist Curator | View content and manage playlists |
| Copyright Manager | View content and manage/verify rights records |
| Support Staff | Manage users and subscriptions |
| Analytics Viewer | View analytics and export aggregate reports |

Custom admin pages check the relevant model or custom permission in addition to
requiring an authenticated staff session. Non-superusers cannot alter
`is_staff`, `is_superuser`, groups, or direct user permissions, preventing
self-escalation. Creators cannot approve their own content unless granted the
explicit `approve_own_audiotrack` permission. Approval and publication remain
separate permissions.

## 4. Custom dashboard pages

- **SunneKatha overview:** twelve summary metrics and compact lists for tracks
  needing attention, uploads, publications, failed processing, pending reviews,
  users, popularity, and scheduled content.
- **Failed audio processing:** stage/date/creator filters, title and filename
  search, safe error summaries, related-object links, and confirmed retries.
- **Pending reviews:** processing, copyright, cover, narrator, and metadata
  readiness indicators; reviewer assignment; guarded bulk review operations.
- **Scheduled publications:** timezone-aware Today, Tomorrow, This week, and
  Later groups with confirmed reschedule, cancel, and publish-now flows.
- **Listening analytics:** preset or custom date ranges, aggregate metrics,
  popular content, delayed-data labeling, and permission-controlled CSV export.
- **Metadata transfer:** authorized CSV export and preview-first, all-or-nothing
  metadata import with dry-run validation and row-level errors.

Dashboard query composition lives in service modules rather than templates.
Expensive non-personal summaries use short-duration caches; permission decisions
and staff-specific state are never cached globally.

## 5. Custom actions

Actions include:

- publish, unpublish, feature, unfeature, submit for review, approve, request
  changes, reject, schedule, and archive;
- retry one or multiple failed processing jobs;
- duplicate literary works, albums, and playlists;
- recalculate playlist positions and remove unavailable tracks;
- activate/deactivate and reorder homepage sections and items;
- verify or revoke permission-document verification;
- grant, extend, cancel, revoke, or restore manually managed subscription access;
- suspend user accounts;
- assign reviewers and export selected metadata.

Sensitive or destructive actions require server-side confirmation. Workflows
validate every selected object, call service-layer operations, respect
permissions, record audit context, and report partial failures rather than
silently skipping invalid records. Scheduling cancellation and publish-now were
also brought behind confirmation during this audit.

## 6. Performance improvements

- Admin querysets use `select_related`, targeted `prefetch_related`, annotations,
  aggregate queries, and `list_select_related` for high-traffic lists.
- Track list querysets defer transcript and waveform fields; list pages never
  render full transcripts or waveform JSON.
- Related-object autocomplete replaces unbounded select widgets.
- Playlist and album relationships use constrained inlines and stable
  server-side ordering.
- Dashboard summaries and sidebar counts are cached briefly where safe.
- Thumbnails request bounded display dimensions and fall back cleanly.
- Query-count regression coverage exists for the dashboard and important model
  administration pages.
- Live inspection found no document-level horizontal overflow or off-screen
  focusable controls at 768, 1024, 1280, or 1440 pixels.

## 7. Security controls

- Django admin authentication, CSRF middleware, secure session behavior, and the
  existing custom user model are preserved.
- Every custom admin view is wrapped with `AdminSite.admin_view` and performs
  model/custom permission checks.
- Publishing, review, upload, audio, playlist, homepage, user, and subscription
  services validate caller authorization instead of trusting the UI alone.
- Private audio and permission documents are delivered by authorized,
  short-lived CloudFront/S3 access services. Django does not proxy audio bytes,
  and list pages do not generate signed URLs.
- CloudFront expiry is constrained to 30–900 seconds at runtime.
- Upload object keys remain server controlled. Admin pages do not expose
  credentials, presigned upload URLs, or construct storage keys directly.
- Permission documents receive extension, MIME, size, and signature validation.
- Ordinary editors receive safe processing error summaries; technical traces are
  restricted to superusers.
- Important changes write administrative audit entries with actor, action,
  object, time, reason, before/after summaries, and request identifier. Passwords,
  tokens, signed URLs, credentials, and file contents are excluded.
- Superuser and permission fields are protected from non-superuser modification.
- Sensitive mass actions and destructive operations require confirmation.

Production deployments must use the production settings, trusted proxy
configuration, exact `ALLOWED_HOSTS`/CSRF origins, HTTPS, and production secrets.
Development wildcard-host or tunnel settings must not be copied to production.

## 8. Tests

Validation completed:

| Check | Result |
| --- | --- |
| `python manage.py check` | Passed, no issues |
| `python manage.py makemigrations --check --dry-run` | Passed, no model changes |
| `python manage.py collectstatic --noinput --dry-run --verbosity 0` | Passed |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed; 318 files formatted |
| Focused admin regression suite | Passed; 41 tests |
| Complete pytest suite | Passed; 594 tests in 11.40 seconds |

The tests cover dashboard access and query behavior, registrations, role
boundaries, workflow transitions, confirmations, ownership, private media,
processing retries and duplicate prevention, playlist ordering, homepage
validation, copyright documents, subscriptions, audit logging, responsive CSS
contracts, and custom page permissions.

The migration command could not query the developer PostgreSQL server from the
sandbox and emitted a connection warning. It still confirmed that model state
requires no new migration. Migration execution is covered by the isolated test
database; deployment should additionally run the migration check against its
actual PostgreSQL instance.

## 9. Remaining limitations

- Real AWS S3, CloudFront signing, IAM, and CDN behavior cannot be exercised
  end-to-end in the local audit; automated tests use controlled mocks.
- The audio-processing administration and retry pipeline are prepared for
  Celery, but actual codec/FFmpeg transformation remains an infrastructure
  boundary where the processing implementation is not enabled.
- Subscription changes are staff-managed foundations, not payment-provider
  events. No payment integration is implied.
- Analytics use delayed aggregate tables and may be incomplete until scheduled
  aggregation tasks have run.
- The admin is optimized for tablets and laptops, not positioned as a
  phone-first editing application.
- Responsive and semantic checks were performed in a live browser, but this is
  not a substitute for a formal WCAG audit with multiple assistive technologies.
- Production readiness still depends on deployment-time environment validation,
  migrations, collectstatic, worker health, storage permissions, backups, and
  monitoring described in the deployment documentation.

No unresolved code-level blocking issue was found in the audited scope.

## 10. Recommended future improvements

1. Exercise the deployment image in a staging environment using production
   settings, real PostgreSQL/Redis, restricted S3 buckets, CloudFront keys, and
   representative IAM roles.
2. Add an FFmpeg-backed integration environment with fixture audio and failure
   injection for processing/recovery drills.
3. Run axe-core and screen-reader acceptance sessions for custom dashboard,
   review, ordering, confirmation, and audio-preview flows.
4. Add browser-level tests for drag-and-drop ordering while retaining the
   existing no-JavaScript fallback tests.
5. Establish performance budgets and production traces for dashboard latency,
   autocomplete, large playlists/albums, and sidebar cache hit rates.
6. Add operational alerts for failed Celery jobs, expiring rights, stale
   analytics, imminent scheduled publications, and audit-log delivery failures.
7. Perform recurring permission-matrix reviews and incident drills for
   publishing reversal, storage-key compromise, subscription correction, backup
   restoration, and rollback.

For nontechnical operating instructions, see
[`admin-dashboard-guide.md`](admin-dashboard-guide.md).
