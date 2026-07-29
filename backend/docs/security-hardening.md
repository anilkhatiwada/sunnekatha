# SunneKatha backend security hardening

## Controls

- JWT authentication uses short-lived access tokens, rotating refresh tokens,
  and refresh-token blacklisting.
- Anonymous and authenticated requests have global DRF limits. Registration,
  login, refresh, password change, direct upload, and stream URL requests use
  stricter scoped limits configured through environment variables.
- Direct uploads are creator/staff-only, owner-scoped, exact-size constrained,
  server-keyed, extension/MIME matched, encrypted, and verified with S3 before
  confirmation. Client filenames are metadata only and never become object keys.
- Public catalog querysets require publication state, publication time, and ready
  processing status. Private playlists and upload sessions are resolved through
  owner-scoped querysets that return `404` to unauthorized users.
- Premium and unpublished stream URLs are authorization-dependent, signed, and
  short-lived. Player/media responses are never stored in the shared public
  cache.
- Write serializers explicitly enumerate fields and reject undeclared input on
  account, creator, playlist, and upload mutation boundaries.
- Unexpected API failures return a generic error envelope. Secrets and internal
  exception messages are not returned to clients.

## Permission audit

| Boundary | Result |
| --- | --- |
| Private playlists | Owner only; staff cannot access user-private playlists |
| Unlisted playlists | Direct URL only; excluded from public lists and shared cache |
| Upload sessions | Creator/staff required and session owner filtered |
| Creator drafts | Narrator or contributor ownership required |
| Rights metadata | Rights-holder contributor or staff required; changes audited |
| Publication | Creator cannot publish; staff-only workflow and admin actions |
| Unpublished tracks | Hidden publicly; stream access limited to staff or linked creator |
| Premium streams | Active subscription/content entitlement or staff required |
| Admin actions | Django model change permission and staff admin access required |

## Production deployment

Supply secrets only through the runtime environment or workload secret manager.
Do not commit Django secrets, CloudFront private keys, AWS credentials, database
credentials, or Redis credentials.

The trusted reverse proxy must remove client-supplied forwarding headers before
setting `X-Forwarded-Proto`. Set `TRUST_X_FORWARDED_PROTO=false` if Django is
directly internet-facing. Enable `USE_X_FORWARDED_HOST` only when the proxy
validates and replaces the forwarded host.

Production CORS and CSRF origins must be explicit HTTPS origins. HSTS, HTTPS
redirection, secure `__Host-` cookies, strict SameSite cookies, clickjacking
protection, MIME sniffing protection, and a same-origin referrer policy are
enabled by production settings.
