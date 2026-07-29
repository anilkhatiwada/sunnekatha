# SunneKatha

[![Backend CI](https://github.com/anilkhatiwada/sunnekathaapp/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/anilkhatiwada/sunnekathaapp/actions/workflows/backend-ci.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)

SunneKatha is a responsive, audio-first platform for Nepali stories, poems,
essays, novels, folk tales, drama, and spoken-word literature. It is built with
Next.js App Router, strict TypeScript, Tailwind CSS, Zustand, TanStack Query,
React Hook Form, Zod, Framer Motion, Lucide, and shadcn/ui conventions.

The frontend ships with typed Nepali mock content and a safe local demo
recording. A Django REST Framework foundation now lives in `backend/`; domain
models and frontend remote adapters are intentionally not implemented yet.

## Requirements

- Node.js 20.19+ on an active LTS line (Node 20, 22, or newer)
- npm 10+
- Python 3.12+ and PostgreSQL 16+ for backend development

## Setup

```bash
git clone <repository-url>
cd <repository-directory>
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The checked-in defaults
run in mock mode. Use an ignored `.env.local` to opt into a remote backend.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_MODE` | `mock` | Selects `mock` or explicitly configured `remote` transport. Pages remain mock-backed until their adapters are migrated. |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Complete Django API base URL, including `/api/v1`. Required in remote mode. |
| `NEXT_PUBLIC_API_TIMEOUT_MS` | `15000` | Timeout for the central API client, in milliseconds. |
| `NEXT_PUBLIC_APP_ENV` | `local` | Public environment label: `local`, `staging`, or `production`. Production remote URLs must use HTTPS. |

Only expose browser-safe values through `NEXT_PUBLIC_*`. Never put secrets,
refresh tokens, or private service credentials in these variables.

The temporary deployed backend uses
`http://13.205.30.123/api/v1`. It may be placed only in an ignored local
environment file and must not be used with real credentials. Replace it with
the final HTTPS API domain before authentication or production deployment.

## Development commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Next.js development server |
| `npm run build` | Create an optimized production build |
| `npm run start` | Serve the production build |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | Run strict TypeScript checks |
| `npm test` | Run Vitest unit and component tests once |
| `npm run test:watch` | Run Vitest in watch mode |
| `npm run test:e2e` | Build and run Playwright journeys |
| `npm run test:e2e:ui` | Build and open Playwright's interactive runner |

Install Playwright's browser once on a new machine:

```bash
npx playwright install chromium
```

Recommended pre-commit verification:

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

## Folder structure

```text
src/
  app/          App Router layouts, loading boundary, and routes
  components/   Reusable cards, layout, player, state, section, and UI elements
  config/       Navigation and application configuration
  data/         Typed Nepali catalog and user-library fixtures
  features/     Route/feature composition and isolated Zustand stores
  lib/          Framework-independent formatters and utilities
  services/     Mock services, API client, auth hooks, errors, and query keys
  test/         Shared Vitest setup and fixtures
  types/        Domain, API response, and pagination contracts
docs/
  api-contract.md
public/
  audio/        Local, rights-safe demo audio
tests/
  e2e/          Playwright user journeys
```

`AGENTS.md` is the canonical source for coding conventions, architecture,
agent responsibilities, and the Architect → Engineer → Reviewer workflow.

## Architecture

- **App Router shell:** the root layout mounts providers, navigation, one
  persistent player UI, and one native `HTMLAudioElement` controller. Route
  changes do not recreate playback state.
- **Server/client boundary:** route files stay small; interactive feature
  components opt into client rendering only when needed.
- **Async state:** TanStack Query owns service request state. Query keys are
  centralized so future mutations can invalidate data predictably.
- **Local domain state:** Zustand stores are deliberately separate. The player
  owns playback and queue state, the library owns favorites/follows/progress,
  and profile preferences have their own store.
- **Persistence:** only queue metadata and safe playback preferences are
  persisted for the player. Library and profile preferences use local storage.
  The `HTMLAudioElement`, transient loading state, errors, mute state, and
  playing state are never persisted.
- **Audio engine:** a single controller synchronizes native audio events,
  Media Session actions, progress checkpoints, keyboard shortcuts, volume,
  seeking, speed, shuffle, and repeat behavior with the player store.
- **Presentation:** reusable typed cards and request-state components avoid
  route-level duplication. `next/image`, responsive sizing, dark design tokens,
  focus styles, reduced-motion behavior, dialogs, and keyboard controls are
  handled centrally.
- **PWA:** the manifest, adaptive icons, and a small service worker support
  mobile installation and an offline app shell. Audio files and API responses
  are intentionally excluded from runtime caching.

## Mock request states

Mock requests support deterministic loading, success, empty, and error states.
Add `mock` to a page URL:

- `?mock=success` — normal content
- `?mock=empty` — successful empty collections
- `?mock=error` — normalized error with retry UI
- `?mock=loading` — extended delay for inspecting skeletons

Examples:

```text
http://localhost:3000/explore?mock=empty
http://localhost:3000/search?q=katha&mock=error
```

## Replacing mocks with a Django API

Page components must continue importing typed functions from `src/services`;
do not fetch directly from a route component.

1. Implement a remote adapter for each service using `apiClient`.
2. Use raw types from `src/types/backend-api.ts` and explicit mappers from
   `src/services/api-mappers.ts`; do not cast backend JSON directly to UI models.
3. Select mock or remote adapters inside the service layer using
   `NEXT_PUBLIC_API_MODE`.
4. Establish JWT sessions with `setAuthTokens`. Tokens are currently stored in
   tab-scoped `sessionStorage` because the backend returns JSON tokens. This is
   an interim design and requires strong XSS controls and HTTPS. Prefer
   same-origin HttpOnly refresh cookies if the backend contract later supports
   them.
5. Keep errors normalized as `ApiError` and use the existing pagination types.
6. Add mutation hooks and invalidate entries from the shared query-key factory.
7. Validate serializer responses at the boundary before enabling remote mode.

Expected endpoints, payloads, authentication behavior, pagination, and a
migration example are documented in
[`docs/api-contract.md`](docs/api-contract.md).

## Backend foundation

Backend setup, Docker, environment variables, migrations, tests, linting, and
schema commands are documented in
[`backend/README.md`](backend/README.md).

## Known limitations

- No Django backend, real account authentication, cloud library sync, billing,
  analytics, or production error monitoring is connected.
- Remote API mode is intentionally not enabled until reviewed service adapters
  exist.
- Mock records reuse one local demo recording; they are representative catalog
  data, not a licensed production audio library.
- Downloads, sharing, sleep timer, audio quality, notifications, and synchronized
  transcript timing are placeholders.
- The aggregate `/playlists` route is a lightweight placeholder; playlist detail
  pages are implemented.
- Search history, preferences, favorites, follows, queue metadata, and listening
  progress are browser-local and can be cleared with site storage.
- Cover art uses an allow-listed remote placeholder host, so images require
  network access. Production assets should move to the project's image CDN.
- Offline audio playback, background downloads, and cross-device playback
  handoff are not implemented. The service worker only provides a lightweight
  offline app shell.
