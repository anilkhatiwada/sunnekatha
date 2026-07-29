# Production-readiness audit

Date: 2026-07-23

## Verdict

The API is ready for a controlled production deployment of catalog, listener,
editorial, entitlement, and streaming capabilities once real AWS, PostgreSQL,
Redis, proxy, backup, and monitoring configuration passes the deployment
checklist. Creator audio ingestion is not end-to-end production-ready because
audio processing is intentionally not implemented.

## Audit results

| Area | Result | Evidence and disposition |
| --- | --- | --- |
| Django checks | Pass | `manage.py check` reports no issues. Production settings fail fast and have dedicated subprocess tests. |
| Migrations | Pass with environment caveat | No migration drift. CI applies migrations on PostgreSQL 17. Local audit could not connect to sandbox-blocked PostgreSQL. |
| Constraints | Pass | UUID identities, publication prerequisites, ordered-item uniqueness, one-per-user relationships/progress, ownership checks, and date/range checks are database-backed where concurrency matters. |
| Indexes | Pass | Public catalog, featured/date, relationship ordering, listener recency, and PostgreSQL search paths are indexed. Avoid speculative duplicates until production plans are measured. |
| Authentication | Pass | Email login, short access tokens, rotated refresh tokens, blacklist, password validation, active-user enforcement, and revocation on password change are covered. JSON refresh storage remains a documented browser limitation. |
| Permissions/IDOR | Pass | Owner-scoped playlists, upload sessions, queues, progress, creator drafts, notifications, and private content have negative tests. Staff-only publishing/analytics paths are explicit. |
| Private media | Pass with operational requirement | Audio storage is private and never serialized. Django returns CloudFront authorization metadata and never proxies bytes. CloudFront OAC and path behavior must be configured exactly as documented. |
| S3 | Pass | Workload-role credentials, private ACLs, encryption, server-controlled keys, lifecycle prefixes, and bucket separation are configured. Production rejects custom S3 endpoints. |
| Upload validation | Fixed | Presigned POST now allows bounded multipart overhead; confirmation still requires exact object size, MIME, encryption, and signature. The former exact multipart-body policy would reject valid browser uploads. |
| CloudFront/premium | Pass | Free, premium, expired, anonymous, creator, staff, and unpublished cases are tested. Premium/restricted URLs are signed for 30–900 seconds. |
| Celery | Partial | Daily analytics task retries database errors with backoff. Production worker safety/timeouts are configured. Audio processing tasks do not exist and are documented as a deployment limitation. |
| Failed processing recovery | Fixed documentation/behavior claim | Admin now says it resets failed records to pending rather than falsely claiming a job was queued. End-to-end retry awaits the audio processor. |
| Caching | Pass | Only public data is globally cached; personalized state is composed separately. Versioned invalidation and cache tests exist. |
| Rate limiting | Fixed | Global and scoped rates use Redis. Production now explicitly sets and validates `DRF_NUM_PROXIES`, preventing client-controlled forwarding chains from defeating identity-based throttles behind the expected proxy count. |
| Logging | Fixed | Production supports JSON logs. Gunicorn access logs no longer include raw query strings, reducing leakage of sensitive query values. Secrets, JWTs, signed URLs, and upload policies remain prohibited. |
| Coverage | Pass | 91.63% measured statement/branch coverage; required floor is 80%. Security, permissions, media, cache, queries, and publication paths have focused tests. |
| OpenAPI | Pass | Schema generation and validation complete without reported errors. Swagger and ReDoc are configured. |
| Frontend compatibility | Partial | Detailed report exists. Backend aliases and additive fields improve compatibility, but frontend services remain mock-backed and secure playback needs an adapter. |
| Docker | Pass | Multi-stage, non-root runtime, build-time static collection, health check, graceful signals, separate roles, and runtime FFmpeg. Compose uses dependency health and one migration service. |
| Deployment docs | Pass | Provider-neutral and AWS reference deployment, migration, proxy, health, backup, rollback, IAM, S3, CloudFront, and operational checklists exist. |

## Production gates

Before traffic is enabled:

1. run CI against PostgreSQL and Redis;
2. build and vulnerability-scan the immutable image;
3. run the image `check` command with the real secret-injected environment;
4. verify S3 Block Public Access, versioning, encryption, lifecycle, and OAC;
5. test free playback, premium allow/deny, and URL expiry against CloudFront;
6. restore an RDS backup in a non-production environment;
7. verify proxy header replacement and the configured `DRF_NUM_PROXIES`;
8. load-test homepage, search, playlist detail, progress, and stream authorization;
9. validate logs contain no JWTs, signed URLs, policies, or secrets;
10. keep creator audio ingestion disabled or operationally controlled until the
    processing pipeline is implemented and tested.
