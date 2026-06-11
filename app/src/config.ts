// Runtime configuration, sourced from the `__*__` constants that Vite injects
// at build time (see `define` in vite.config.ts and the declarations in
// globals.d.ts). Centralised here so the rest of the app imports plain values
// rather than reaching for build-time globals directly.

export const config = {
  /** Event Central API base URL. */
  apiBaseUrl: __API_BASE_URL__,
  /** This SPA's own base URL (used for redirect URIs). */
  appBaseUrl: __APP_BASE_URL__,
  /** OAuth client id sent with token requests. */
  clientId: __APP_CLIENT_ID__,
  /** Space-delimited scopes requested at login. */
  defaultScope: __APP_DEFAULT_SCOPE__,
  /** Optional path the app is served under. */
  pathPrefix: __APP_PATH_PREFIX__,
  /** ISO timestamp of the build. */
  buildTime: __BUILD_TIME__,
} as const;
