# First public release production-readiness audit

**Audit date:** 2026-08-12  
**Scope:** Next.js frontend, Django API/admin, PostgreSQL/Redis integration,
Celery, S3/CloudFront media, deployment configuration, tests, dependencies, and
documentation.  
**Recommendation:** **NO-GO until the release gates below are completed.**

The source tree is close to release quality. All automated unit, integration,
schema, lint, type, build, and isolated browser checks pass after the fixes in
this audit. The remaining blockers are operational or require an explicit
product/legal decision and cannot be proved from the repository alone.

## Release gates

Do not announce the first public release until all of these are recorded as
complete:

1. Deploy the patched dependency set from this audit. The currently running
   release must not remain on Next.js 16.2.10, Sharp 0.34.5, or cryptography
   46.x.
2. Decide whether production must set `ENFORCE_EDITORIAL_RIGHTS_READINESS=true`.
   If it remains false, obtain and record an explicit editorial/legal acceptance
   of the risk before publishing real content.
3. Create a PostgreSQL backup and perform a restore drill into a non-production
   database. Confirm that uploaded originals and permission documents have an
   independently documented recovery procedure.
4. Run the PostgreSQL 17 + Redis CI job on the exact release commit, including
   migrations and OpenAPI validation.
5. Run live smoke tests for email and Google login, access-token refresh, logout,
   free and premium playback, direct S3 upload/confirmation/processing, admin
   publication, private playlist isolation, and mobile playlist actions.
6. Confirm monitoring for disk exhaustion, process failure, backup failure,
   Celery queue growth, and repeated HTTP 5xx responses. The repository has
   structured logs and health endpoints but cannot prove external alerting.

Once these six gates pass, the recommendation becomes **GO for a small,
low-traffic first release**.

## 1. Critical issues that must be fixed before release

### Fixed in this audit

- **Vulnerable production JavaScript dependencies.** Next.js 16.2.10 and Sharp
  0.34.5 had high-severity advisories. Updated to Next.js 16.3.0, matching
  `eslint-config-next`, and Sharp 0.35.3. Patched PostCSS and nanoid are pinned as
  transitive overrides. `npm audit --omit=dev` now reports zero vulnerabilities.
- **Vulnerable Python cryptography constraint.** The `<47` constraint resolved
  to cryptography 46.0.7 with four advisories. The production constraint now
  uses the patched 50.x line. `pip-audit` reports no known vulnerabilities.
- **No frontend CI gate.** Added a pull-request/main workflow for install,
  production dependency audit, lint, type checks, tests, and production build.
- **E2E environment contamination.** Browser tests were compiling against the
  checked-in production API while asserting mock fixtures. The E2E scripts now
  set their build mode explicitly.
- **Mock homepage playback regression.** Homepage cards always requested the
  remote stream endpoint, even when a safe local mock track already carried an
  audio URL. Mock mode now plays that local source; production still uses the
  secure stream handshake.

### Still blocking

- The patched dependencies and configuration have not been deployed by this
  audit. The live version must be verified after deployment.
- Rights-readiness enforcement defaults to false in the example and was
  intentionally relaxed in production. This can allow editorial publication
  without the otherwise supported permission/document gate.
- A successful backup restore and external alert path are not verifiable from
  source code.

## 2. Important issues that should be fixed

- JWT access and refresh tokens are stored in `localStorage`. This matches the
  current JSON-token API and rotation behavior, but any successful XSS can steal
  the refresh token. Prefer an HttpOnly, Secure, SameSite refresh cookie in a
  future auth-contract change.
- The frontend adds frame, MIME-sniffing, referrer, and browser-feature headers,
  but no Content Security Policy is enforced. Add a nonce-based CSP after
  validating Google Identity Services, Next.js scripts, images, and CloudFront
  media in staging. A rushed CSP could break login, so it was not added blindly.
- Remote mode intentionally omits author collections, related-author
  recommendations, narrator playlists, and personal profile statistics because
  corresponding APIs do not exist. The UI hides empty sections, but these are
  incomplete product features.
- Payment checkout, external email/push delivery, offline downloads, and
  cross-device playback handoff are not implemented. Release messaging must not
  imply that they are available.
- The full-player download control remains a visible “coming soon” action.
  Consider hiding it for the first release to avoid misleading users.
- The default production topology is a single Lightsail host containing web,
  PostgreSQL, Redis, and workers. It meets the cost target but has a single-host
  failure domain and must be paired with tested off-host backups.
- OpenAPI/Swagger/ReDoc endpoints are public. They do not expose secrets, but
  decide explicitly whether API discovery is desired in the public release.
- One high-severity advisory remains in a nested `brace-expansion` used only by
  the ESLint development toolchain. It is not in the production dependency tree;
  upgrade when the upstream ESLint/TypeScript ESLint tree resolves it.

## 3. Minor improvements

- Replace the Playwright `next start` web-server command with a dedicated
  standalone-launch script to remove the framework warning while preserving the
  copied `public` and `.next/static` assets.
- Add a supported dead-code analyzer to development dependencies once its Node
  runtime support matches the project LTS policy. The attempted current Knip
  release does not support the local odd-numbered Node 21 runtime.
- Continue splitting the very large catalog `ModelAdmin` module when doing so
  improves ownership or tests; do not rewrite it solely for style.
- Add frontend bundle-budget reporting and production Web Vitals collection
  when a privacy-conscious monitoring destination is selected.

## 4. Unused/dead code removed

- Removed the unreferenced `profile-service.ts` and its barrel export. It
  returned fabricated listening statistics and had no runtime consumer.
- No other suspicious files were deleted. Mock catalog assets and services are
  still used by local development and E2E tests, so they are not dead code.
- Test credentials remain confined to tests and the development-only seed
  command. The seed command refuses to run with `DEBUG=False`.

## 5. Incomplete features or TODOs discovered

- Offline/download support.
- Payment-provider integration and self-service billing.
- External email and push notification delivery.
- Personal listening-statistics API.
- Dedicated author/narrator playlist recommendation APIs.
- Trending search is currently a stable placeholder rather than an aggregate
  query.
- Automatic playlists are represented as a placeholder type but are not
  generated.
- Some older analysis documents describe the historical mock-only phase. They
  remain useful as audit history; current status is now linked from the root
  README.

## 6. Security findings

### Controls verified in code and tests

- Production fails fast for weak Django secrets, wildcard hosts, non-HTTPS
  origins, invalid database/Redis transport, missing S3 buckets, and missing
  CloudFront signing material.
- DEBUG is disabled in production; HSTS, proxy HTTPS handling, secure cookies,
  `nosniff`, referrer policy, and clickjacking protection are configured.
- DRF authentication, scoped throttles, safe exception normalization, upload
  size/type/content validation, server-generated object keys, ownership checks,
  admin permissions, and mass-assignment protections have tests.
- S3 originals, processed audio, and permission documents use private storage.
  Stream and admin preview services issue CloudFront/private-storage URLs rather
  than proxying bytes or returning raw credentials.
- Premium and unpublished streaming authorization, expired entitlements,
  private/unlisted playlists, creator ownership, and staff actions have tests.
- Secret-pattern review found no tracked AWS keys, private keys, or environment
  secret files. Matches were test passwords or password-handling code.

### Residual risk

- Browser token storage and absence of CSP increase XSS impact.
- Rights enforcement is an explicit production policy switch and is currently
  documented as false in the example.
- Live IAM least privilege, S3 public-access blocks, CloudFront behavior/order,
  key rotation, and Cloudflare settings require console verification.

## 7. Performance findings

- Backend tests cover bounded queries for homepage, track/playlist details,
  progress, queues, search, and admin lists. The complete suite passes.
- Public homepage/catalog/detail responses use short Redis caches; personalized
  data is not globally cached. Cache invalidation has dedicated tests.
- List serializers omit transcript/waveform-heavy fields; admin querysets defer
  large fields and use relations/annotations where tested.
- Direct-to-S3 uploads and CloudFront delivery avoid sending media bytes through
  Django. Byte-range playback is delegated to CloudFront.
- The frontend centralizes request caching through TanStack Query and avoids
  service-worker caching for API/audio/range requests.
- No release-blocking N+1 or unbounded list regression was reproduced. Query
  plans and cache behavior still need PostgreSQL/Redis CI and production-volume
  observation.

## 8. Documentation changes made

- Replaced the obsolete root README that claimed the application was mock-only.
  It now documents the real architecture, URLs, setup, environments, Redis,
  Celery, FFmpeg, AWS integration, testing, seed safeguards, frontend/API flow,
  deployment, and current limitations.
- Corrected the backend README’s frontend-integration status.
- Updated integration status with current test counts and dependency audit
  results.
- Removed duplicate throttle variables from `.env.example` and retained the
  production-compatible values once.
- Added this audit and release-gate checklist.

## 9. Tests/checks performed and results

| Check | Result |
| --- | --- |
| Frontend ESLint | Pass with 7 existing internal-navigation warnings; no errors |
| TypeScript `tsc --noEmit` | Pass |
| Vitest | 89/89 pass |
| Next.js production build | Pass on 16.3.0 |
| Playwright isolated journeys | 5/5 pass after E2E fixes |
| Production npm audit | Pass, zero known vulnerabilities |
| Full npm audit | One high advisory in development-only ESLint dependency |
| Django system check | Pass |
| Migration drift (`--check --dry-run`) | Pass |
| Ruff lint | Pass |
| Ruff format | Two files fixed; final check passes |
| Django pytest | 628/628 pass |
| Backend coverage | 86.9%, threshold 80% |
| OpenAPI generation/validation | Pass with `--fail-on-warn` |
| Production Python `pip-audit` | Pass, zero known vulnerabilities |
| Secret-pattern scan | No tracked production credentials/private keys found |
| `git diff --check` | Pass |

The local default test suite uses SQLite and locmem cache. A deliberate run with
local PostgreSQL but without Redis produced cache/readiness failures; this was an
environment mismatch, not a product assertion. PostgreSQL + Redis parity is
covered by CI and remains a release gate on the final commit.

## 10. Manual verification required

- Exact live commit/version and all systemd services after deployment.
- Confirm whether the seven deliberate full-page internal redirects should remain
  hard reloads at authentication/session boundaries or migrate to router pushes.
- Google OAuth allowed origins/client configuration and session persistence
  through refresh rotation.
- Email/password registration, login throttling, logout blacklist, password
  change, and invalid-token behavior on the public domains.
- Direct upload from representative mobile/desktop browsers, S3 object metadata,
  Celery processing success/failure/retry, and published playback.
- CloudFront custom hostname, cover images, free byte ranges, premium signatures,
  expiration, and direct-S3 denial.
- Anonymous/private/unlisted playlist behavior and authenticated mobile add,
  remove, reorder, and duplicate flows.
- Admin static assets, private audio preview, permission-document delivery,
  publication/review actions, and role boundaries.
- Responsive and keyboard review at 768, 1024, 1280, and 1440 pixels, plus a
  real iOS Safari and Android Chrome pass.
- PostgreSQL restore, S3/document recovery, rollback, TLS renewal, disk capacity,
  log retention, and external alerts.

## Final verdict

**NO-GO at this moment.** The code-level blockers discovered during the audit
have been fixed and automated evidence is strong, but the first public release
must wait for deployment of those fixes, PostgreSQL/Redis CI on the exact commit,
a tested backup restore, a rights-enforcement decision, and live end-to-end smoke
verification. After those gates pass, no remaining source-code finding prevents
a small public launch.
