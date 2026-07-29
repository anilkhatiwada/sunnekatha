# Django Unfold setup

SunneKatha uses Django Unfold to present the existing Django administration site.
The integration intentionally retains Django's default global admin site,
authentication, `/admin/` URL, custom user model, permissions, registrations,
and admin actions.

## Dependency and installation

`backend/requirements/base.txt` pins Django Unfold to the compatible
`>=0.101,<0.102` release series. Install the normal environment requirements:

```bash
cd backend
python -m pip install -r requirements/local.txt
```

Unfold requires Python 3.12 or newer in this release series. It is listed before
`django.contrib.admin` in `INSTALLED_APPS`, as required by Unfold. No separate
`AdminSite` or Django project was created; Unfold enhances the global
`admin.site`, and `config/urls.py` continues to mount it at `/admin/`.

## Configuration

The shared `UNFOLD` setting in `config/settings/base.py` defines:

- site title: `SunneKatha Administration`;
- site header: `SunneKatha`;
- site subtitle: `Audio Literature Management`;
- a SunneKatha S monogram for the site icon;
- a matching SVG favicon and branded S-monogram login illustration;
- a warm charcoal/brown neutral palette with muted gold and orange action colors;
- an 8px border radius that keeps controls compact without appearing severe;
- built-in light/dark mode switching; no mode is forced;
- searchable sidebar navigation, model command search, and the complete
  applications menu;
- explicit `LOCAL`, `STAGING`, or `PRODUCTION` environment labels;
- an empty dashboard context callback for future dashboard data;
- a minimal dashboard sidebar entry while retaining the all-applications menu.

`SITE_TITLE` is also the title shown by Unfold's login template. Local, test, CI,
and image-build settings display `LOCAL`; production settings always display
`PRODUCTION`. A staging deployment should set `ADMIN_ENVIRONMENT=STAGING`. The
production badge uses Unfold's restrained warning variant so it remains distinct
without turning the entire interface into an alarm state.

### Sidebar information architecture

The sidebar groups high-frequency work into collapsible Dashboard, Content,
Editorial, Taxonomy, Audio Operations, Rights, Audience, and System sections.
Every model-backed item checks the user's Django `view` or `change` permission
before rendering. “All applications” remains enabled, so lower-frequency
registered models are still reachable subject to the same Django permissions.

Operational entries reuse named admin changelist URLs with filters:

- Featured Content, Scheduled Publications, Processing Queue, Failed Processing,
  Media Files, and Copyright Licenses use catalog changelists;
- Rights Holders uses filtered content contributors;
- Permission Documents uses the immutable rights/license audit;
- Staff uses the user changelist filtered to staff accounts;
- Permissions opens Groups, where Django permissions are assigned;
- Background Jobs opens daily platform metrics, the persisted output of the
  currently implemented analytics job;
- Application Settings returns to the admin overview because no application
  settings model currently exists.

Pending uploads, processing-queue tracks, failed tracks, and scheduled tracks
have count badges. Each count is cached for 60 seconds and is not queried when
the current user lacks access to its model. No per-row or cross-model aggregate
queries run while building navigation.

### Dashboard homepage

The project-level `templates/admin/index.html` is populated through
`config.admin.dashboard_callback` and the read-only query builder in
`apps.common.admin_dashboard`. It displays permission-aware headline metrics and
ten compact operational tables for publishing, uploads, reviews, audience
activity, rankings, and scheduling.

The dashboard:

- batches all track-state headline counts into one aggregate query;
- limits every table to six records;
- uses `select_related` for work, author, and narrator labels;
- explicitly defers transcripts, waveform JSON, descriptions, and audio file
  fields;
- uses cached `play_count_cache` for the most-played list;
- aggregates monthly listening hours and author/narrator popularity from daily
  analytics tables;
- catches unavailable analytics storage and renders a clear unavailable state;
- links cards, rows, and “View all” actions through named admin URLs;
- omits metrics and sections when the user lacks the relevant Django model
  permission.

The namespaced dashboard stylesheet is
`apps/common/static/admin/css/sunnekatha-dashboard.css`. Its metric grid adapts
automatically, operational tables use two columns on laptop widths and one column
on tablet widths, and wide compact tables scroll within their cards rather than
expanding the page.

Callbacks live in `config/admin.py`. The dashboard callback intentionally performs
no queries. Brand assets live under
`apps/common/static/admin/brand/` so Django's staticfiles discovery and the
production manifest pipeline both collect them.

All project `ModelAdmin` and tabular inline classes use Unfold's compatible base
classes. Their registrations, fields, actions, permissions, URLs, and business
services are unchanged. The custom user admin uses Unfold-styled forms whose
`Meta.model` remains `accounts.User`; email remains the login identifier.

## Validation commands

Run these from `backend/` with the environment's Python:

```bash
python manage.py check --settings=config.settings.local
python manage.py makemigrations --check --dry-run --settings=config.settings.test
python manage.py collectstatic --noinput --clear --settings=config.settings.build
pytest
ruff check .
ruff format --check .
```

Production settings require the environment variables documented in the main
README. Validate them without weakening production checks:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput
```

The production static backend is WhiteNoise
`CompressedManifestStaticFilesStorage`. A successful `collectstatic` must include
Unfold's assets and the three `admin/brand/sunnekatha-*.svg` files.

## Rollback

The integration has no migrations or data changes. To roll it back, restore the
admin classes to Django's base classes, remove the shared `UNFOLD` setting and
branding assets, remove `unfold` from `INSTALLED_APPS`, and remove the dependency.
The existing `/admin/` URL and model registrations remain the rollback target.
