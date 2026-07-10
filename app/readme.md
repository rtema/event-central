# Event Central — User Administration

A React + Vite single-page app for managing users on the Event Central
e-invoicing platform: accounts, sign-in (auth) methods, access scopes, and the
per-user schemaless data store. It talks to the Event Central OpenAPI surface
(`/auth/*` and `/api/v1/users/*`).

## Highlights

- **Robust, silent, cross-tab token refresh** (the core of the app — see below).
- **Mantine 7** UI, **Tabler** icons, **TanStack Table** for the user list.
- **React Router** for routing, **SWR** for data fetching/revalidation.
- **Axios** transport with token-aware interceptors.
- **Lingui** i18n with full **English and German** catalogs.
- **dayjs** for locale-aware date formatting.
- Tested with **Vitest** (31 tests covering the refresh/cross-tab logic).

## The cross-tab token fetcher

The requirement was a fetcher for protected endpoints that _silently_ revalidates
tokens and stays correct across multiple browser tabs. The implementation lives
in `src/api/` and is split into small, individually testable pieces:

| File              | Responsibility                                                                                                                   |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `storage.ts`      | Token persistence. `localStorage` is the cross-tab source of truth; an in-memory variant backs the tests.                        |
| `lock.ts`         | Cross-tab mutual exclusion. Uses the **Web Locks API** (`navigator.locks`) when available, with an in-memory fallback.           |
| `broadcast.ts`    | Cross-tab messaging over the validated **`broadcast-channel`** package (BroadcastChannel with localStorage/indexedDB fallbacks). |
| `tokenManager.ts` | Owns the token lifecycle: single-flight refresh, cross-tab serialisation, and change/logout propagation.                         |
| `client.ts`       | The axios instance + interceptors that attach the bearer token and transparently refresh-and-replay on a `401`.                  |
| `instance.ts`     | The app-wide singleton wiring of the above.                                                                                      |

**How a silent refresh works**

1. A protected request gets a `401`. The response interceptor calls
   `tokenManager.refresh()` once (guarded by a `_retry` flag so a request is
   never retried twice).
2. `refresh()` is **single-flight within a tab**: concurrent `401`s share one
   in-flight promise, so a burst of failures triggers exactly one network call.
3. `refresh()` is also **single-flight across tabs**: the network call runs
   inside a Web Lock. Whichever tab acquires the lock refreshes; the others wait.
4. **Double-checked locking**: once inside the lock, the manager re-reads shared
   storage. If another tab already rotated the token (the stored access token no
   longer matches the stale one we set out to replace), it adopts that result
   instead of making a redundant call.
5. On success the new tokens are written to storage and a `tokens-updated`
   message is broadcast; every tab updates its reactive state and the original
   request is replayed with the fresh token.
6. On failure the session is cleared and a `logged-out` message is broadcast, so
   all tabs return to the login screen together.

The refresh call itself uses a _bare_ axios instance with no interceptors, so a
`401` during refresh can never recurse back into the refresh logic. The `/auth/*`
token, revoke, password-reset and passwordless endpoints are recognised as auth
endpoints and never carry a bearer token nor trigger a retry; `/auth/userinfo`
is treated as protected and benefits from the same silent refresh.

## Project layout

```
src/
  api/            token fetcher, axios client, typed endpoints, app singleton
    __tests__/    Vitest suites for the refresh/cross-tab behaviour
  auth/           AuthProvider (React context) + useAuth hook
  components/     AppLayout, ProtectedRoute, language/theme toggles, QueryState
  hooks/          SWR data hooks (users, scopes, history, data)
  pages/          Login, PasswordReset, UsersList, UserDetail (+ tabs), NotFound
  tables/         TanStack-powered users table
  locales/        Lingui catalogs (en, de) as .po files
  config.ts       runtime configuration from VITE_* env vars
  i18n.ts         Lingui setup with on-demand locale loading
  theme.ts        Mantine theme
```

## Getting started

```bash
npm install
cp .env.example .env        # then edit as needed
npm run dev                 # http://localhost:5173
```

### Environment variables

| Variable             | Default                                       | Purpose                                                                               |
| -------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------- |
| `VITE_API_BASE_URL`  | `http://localhost:7435`                       | Event Central API base URL. The EU node is `https://eu-01.event-central.tema-dev.de`. |
| `VITE_CLIENT_ID`     | `event-central-admin`                         | OAuth client id used in token requests.                                               |
| `VITE_DEFAULT_SCOPE` | `users:read:all users:write:all backend:read` | Space-delimited scopes requested at login.                                            |

## Scripts

| Script                 | What it does                                                       |
| ---------------------- | ------------------------------------------------------------------ |
| `npm run dev`          | Start the Vite dev server.                                         |
| `npm run build`        | Typecheck (`tsc --noEmit`) then build to `dist/`.                  |
| `npm run preview`      | Serve the production build locally.                                |
| `npm test`             | Run the Vitest suite once.                                         |
| `npm run test:watch`   | Run Vitest in watch mode.                                          |
| `npm run lint`         | Typecheck without emitting.                                        |
| `npm run i18n:extract` | Extract translatable strings into the `.po` catalogs.              |
| `npm run i18n:compile` | Compile the catalogs (also done automatically by the Vite plugin). |

## Internationalisation

Strings are wrapped in Lingui's `<Trans>` / `t` macros and extracted to
`src/locales/{en,de}/messages.po`. English and German are both fully translated.
The active locale is detected from the stored preference, then the browser
language, and can be switched at runtime from the header; the choice is persisted
and also drives dayjs date formatting. Only the active locale's catalog is loaded
(via dynamic import), so each language is its own small chunk.

## Testing

```bash
npm test
```

The suite focuses on the parts most likely to break and hardest to verify by
hand: single-flight refresh within a tab, cross-tab serialisation with
double-checked locking, the silent refresh-and-replay token swap, the absence of
retry loops, refresh-failure cleanup + logout broadcast, non-401 pass-through,
and real propagation through the `broadcast-channel` package.

## Deployment (nginx / Apache)

This is a static SPA: build it and serve `dist/` behind your web server, with a
history-API fallback so deep links resolve to `index.html`.

```bash
npm run build
# upload the contents of dist/ to your document root
```

**Apache** — a ready-to-use `public/.htaccess` ships in the build output
(`dist/.htaccess`). It rewrites unknown paths to `index.html`, long-caches
hashed assets, and revalidates the HTML entry point.

**nginx** — equivalent server block:

```nginx
server {
    listen 80;
    server_name admin.example.com;
    root /var/www/event-central-admin;   # the dist/ contents
    index index.html;

    # Long-cache content-hashed assets.
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # History-API fallback for the SPA.
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Notes & assumptions

- Modelled strictly against the user-management surface of the OpenAPI spec.
  Auth-method secrets are shown once on creation (the UI surfaces this clearly);
  auth methods are disabled (soft-deleted) rather than edited, matching the API.
- User deletion is a soft delete; deleted users can be restored.
- The per-user data endpoint replaces the whole object on save (no server-side
  merge), which the Data tab makes explicit.
