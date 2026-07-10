// Auth actions for the UI. All requests go through the authed axios instance
// (`api`); the token/revoke/reset/passwordless endpoints are recognised as
// auth endpoints by the client interceptors, so they never carry a bearer
// token nor trigger a refresh-retry loop. `/auth/userinfo` IS protected, so it
// transparently benefits from the silent refresh + replay.
import { config } from "../config";
import { api } from "./instance";
import { tokenSetFromResponse, tokenStore } from "./tokenStore";
import type {
  AuthPasswordlessStartRequest,
  AuthPasswordResetConfirmRequest,
  AuthPasswordResetStartRequest,
  AuthTokenRequest,
  AuthTokenResponse,
  AuthUserinfoResponse,
} from "./types";

async function requestToken(body: AuthTokenRequest): Promise<void> {
  const { data } = await api.post<AuthTokenResponse>("/auth/token", {
    client_id: config.clientId,
    scope: config.defaultScope,
    ...body,
  });
  tokenStore.set(tokenSetFromResponse(data));
}

export async function loginWithPassword(params: {
  username: string;
  password: string;
  scope?: string;
  clientId?: string;
}): Promise<void> {
  await requestToken({
    grant_type: "password",
    username: params.username,
    password: params.password,
    ...(params.scope ? { scope: params.scope } : {}),
    ...(params.clientId ? { client_id: params.clientId } : {}),
  });
}

export async function loginWithOtp(params: {
  username: string;
  otp: string;
  scope?: string;
  clientId?: string;
}): Promise<void> {
  await requestToken({
    grant_type: "http://auth0.com/oauth/grant-type/passwordless/otp",
    username: params.username,
    otp: params.otp,
    ...(params.scope ? { scope: params.scope } : {}),
    ...(params.clientId ? { client_id: params.clientId } : {}),
  });
}

export async function startPasswordless(
  body: AuthPasswordlessStartRequest,
): Promise<void> {
  await api.post("/auth/passwordless/start", body);
}

export async function startPasswordReset(
  body: AuthPasswordResetStartRequest,
): Promise<void> {
  await api.post("/auth/password-reset/start", body);
}

export async function confirmPasswordReset(
  body: AuthPasswordResetConfirmRequest,
): Promise<void> {
  await api.post("/auth/password-reset/confirm", body);
}

export async function fetchUserinfo(): Promise<AuthUserinfoResponse> {
  const { data } = await api.get<AuthUserinfoResponse>("/auth/userinfo");
  return data;
}

/** Revoke the refresh token server-side (best effort), then clear locally. */
export async function logout(): Promise<void> {
  const tokens = tokenStore.get();
  if (tokens?.refreshToken) {
    try {
      await api.post("/auth/revoke", { token: tokens.refreshToken });
    } catch {
      // Local logout must always succeed even if the network call fails.
    }
  }
  tokenStore.clear();
}
