// Token store facade for the UI/auth layer.
//
// This is a thin adapter over the battle-tested `TokenManager` (see
// tokenManager.ts + its unit tests). The TokenManager owns persistence
// (localStorage), the single-flight cross-tab refresh, and broadcast
// propagation; this facade just exposes the small surface the React layer
// needs (get / set / clear / subscribe) in the shape it expects.
import { tokenManager } from "./instance";
import { mapTokenResponse } from "./tokenManager";
import type { StoredTokens } from "./storage";
import type { AuthTokenResponse } from "./types";

export type TokenSet = StoredTokens;

/** Build a TokenSet from a raw `/auth/token` response. */
export function tokenSetFromResponse(res: AuthTokenResponse): TokenSet {
  return mapTokenResponse(res);
}

export const tokenStore = {
  get(): TokenSet | null {
    return tokenManager.getTokens();
  },
  set(tokens: TokenSet): void {
    tokenManager.setTokens(tokens);
  },
  clear(): void {
    tokenManager.clear();
  },
  hasSession(): boolean {
    return tokenManager.isAuthenticated();
  },
  /** Notified on every token change in this tab and from other tabs. */
  subscribe(listener: (tokens: TokenSet | null) => void): () => void {
    return tokenManager.onTokensChange(listener);
  },
};
