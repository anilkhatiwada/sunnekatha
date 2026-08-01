# Frontend deployment

The production frontend runs as a Next.js standalone server on the same
Lightsail instance as the Django API. Nginx routes frontend requests to port
3000 and preserves Django routes under `/api/`, `/admin/`, `/static/`, and
`/media/`.

The production deployment is built with:

```bash
NEXT_PUBLIC_API_MODE=remote
NEXT_PUBLIC_API_BASE_URL=https://api.sunnekatha.com/api/v1
NEXT_PUBLIC_APP_ENV=production
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<google-oauth-web-client-id>
```

`NEXT_PUBLIC_GOOGLE_CLIENT_ID` is a public browser identifier, not a client
secret. It must be present when `next build` runs; adding it only to the runtime
service environment will not enable Google Identity Services in an already-built
bundle. Keep the matching `GOOGLE_OAUTH_CLIENT_ID` configured in the Django
backend environment.

The Nginx configuration in this directory provides:

- `sunnekatha.com` → Next.js on `127.0.0.1:3000`;
- `api.sunnekatha.com` → Django/Gunicorn on `127.0.0.1:8000`;
- `www.sunnekatha.com` → permanent redirect to the apex domain;
- HTTP → HTTPS redirects for all configured domains.

TLS uses a Let's Encrypt certificate installed at
`/etc/letsencrypt/live/sunnekatha.com/`. Certbot's systemd timer handles renewal.
Validate renewal after installation with:

```bash
sudo certbot renew --dry-run
```

Before reloading an edited Nginx configuration:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

The previous frontend release remains under `/srv/sunnekatha/frontend/releases/`.
Rollback by repointing `/srv/sunnekatha/frontend/current` to the preceding
release and restarting `sunnekatha-frontend.service`.

Cloudflare should use **Full (strict)** SSL/TLS mode. Keep records DNS-only while
issuing or troubleshooting origin certificates; proxy them only after direct
origin HTTPS validation succeeds.

HSTS should remain disabled until every intended subdomain is HTTPS-ready.
