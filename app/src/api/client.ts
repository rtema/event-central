// Axios client wired to the TokenManager.
//
// - A *bare* axios instance (no interceptors) performs the refresh call, so a
//   401 during refresh can never recurse back into the refresh logic.
// - The main client attaches the bearer token on every request and, on a 401,
//   transparently refreshes once and replays the original request.
// - Because TokenManager.refresh() is single-flight + cross-tab locked, a burst
//   of simultaneous 401s produces exactly one refresh.

import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";
import {
  BroadcastChannelAuthChannel,
  NoopAuthChannel,
  type AuthChannel,
} from "./broadcast";
import { createCrossTabLock, type CrossTabLock } from "./lock";
import { LocalTokenStorage, type TokenStorage } from "./storage";
import { TokenManager, type RefreshFn } from "./tokenManager";
import type { AuthTokenResponse } from "./types";

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _triggerToken?: string | null;
}

const AUTH_PATHS = [
  "/auth/token",
  "/auth/revoke",
  "/auth/passwordless/start",
  "/auth/password-reset/start",
  "/auth/password-reset/confirm",
];

/** Endpoints that must never carry a bearer token nor trigger a refresh-retry. */
export function isAuthEndpoint(url?: string): boolean {
  if (!url) return false;
  return AUTH_PATHS.some((p) => url === p || url.endsWith(p));
}

/** Normalised request error surface used by the UI (toasts, retry rules). */
export interface RequestError {
  message: string;
  status?: number;
  code?: string;
  /** Server-provided correlation id, handy to surface in support tickets. */
  correlationId?: string;
}

/**
 * Turn any thrown value (axios error, network error, plain Error) into a
 * stable, display-ready shape. Prefers the API's structured error payload
 * (`Error.message` / `Error.error` or OAuth `error_description`).
 */
export function toRequestError(err: unknown): RequestError {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const data = err.response?.data as
      | {
          message?: string;
          error?: string;
          error_description?: string;
          code?: string | number;
          correlationId?: string;
        }
      | undefined;
    const message =
      data?.message ??
      data?.error_description ??
      (typeof data?.error === "string" ? data.error : undefined) ??
      err.message;
    return {
      message: message || "Request failed",
      status,
      code: data?.code != null ? String(data.code) : err.code,
      correlationId: data?.correlationId,
    };
  }
  if (err instanceof Error) return { message: err.message };
  return { message: "Unknown error" };
}

export interface ApiClientOptions {
  baseURL: string;
  clientId: string;
  scope?: string;
  storage?: TokenStorage;
  lock?: CrossTabLock;
  channel?: AuthChannel;
  /** Override the refresh network call (tests inject a stub). */
  refreshFn?: RefreshFn;
}

export interface ApiClient {
  client: AxiosInstance;
  tokenManager: TokenManager;
}

export function createApiClient(opts: ApiClientOptions): ApiClient {
  const { baseURL, clientId, scope } = opts;

  // Bare instance: only used to exchange the refresh token.
  const bare = axios.create({ baseURL });

  const refreshFn: RefreshFn =
    opts.refreshFn ??
    (async (refreshToken: string): Promise<AuthTokenResponse> => {
      const { data } = await bare.post<AuthTokenResponse>("/auth/token", {
        grant_type: "refresh_token",
        refresh_token: refreshToken,
        client_id: clientId,
        ...(scope ? { scope } : {}),
      });
      return data;
    });

  const tokenManager = new TokenManager({
    storage: opts.storage ?? new LocalTokenStorage(),
    lock: opts.lock ?? createCrossTabLock(),
    channel: opts.channel ?? new NoopAuthChannel(),
    refreshFn,
  });

  const client = axios.create({ baseURL });

  // Request: attach bearer token for protected endpoints.
  client.interceptors.request.use((config: RetryableConfig) => {
    if (!isAuthEndpoint(config.url)) {
      const token = tokenManager.getAccessToken();
      if (token) {
        config.headers.set?.("Authorization", `Bearer ${token}`);
        config._triggerToken = token;
      }
    }
    return config;
  });

  // Response: on 401, refresh once and replay.
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const config = error.config as RetryableConfig | undefined;
      const status = error.response?.status;

      if (
        !config ||
        status !== 401 ||
        config._retry ||
        isAuthEndpoint(config.url)
      ) {
        return Promise.reject(error);
      }

      config._retry = true;
      try {
        const tokens = await tokenManager.refresh(config._triggerToken);
        config.headers.set?.("Authorization", `Bearer ${tokens.accessToken}`);
        return client(config);
      } catch {
        // Refresh failed: TokenManager has already cleared state + broadcast
        // logout. Surface the original 401 to the caller.
        return Promise.reject(error);
      }
    },
  );

  return { client, tokenManager };
}

/** Browser factory: builds the cross-tab channel from `broadcast-channel`. */
export async function createBrowserAuthChannel(): Promise<AuthChannel> {
  const { BroadcastChannel } = await import("broadcast-channel");
  return new BroadcastChannelAuthChannel(
    new BroadcastChannel("event-central.auth") as never,
  );
}
