# Frontend deployment

The production frontend runs as a Next.js standalone server on the same
Lightsail instance as the Django API. Nginx routes frontend requests to port
3000 and preserves Django routes under `/api/`, `/admin/`, `/static/`, and
`/media/`.

The initial IP deployment is built with:

```bash
NEXT_PUBLIC_API_MODE=remote
NEXT_PUBLIC_API_BASE_URL=http://13.205.30.123/api/v1
NEXT_PUBLIC_APP_ENV=staging
```

This temporary configuration allows same-origin browser testing over the
instance IP. Before public production launch, rebuild with:

```bash
NEXT_PUBLIC_API_MODE=remote
NEXT_PUBLIC_API_BASE_URL=https://api.sunnekatha.com/api/v1
NEXT_PUBLIC_APP_ENV=production
```

Do not enable production mode with an HTTP API URL. Configure DNS, origin HTTPS,
the restricted Django CORS/CSRF origin lists, and Nginx TLS before the production
rebuild.
