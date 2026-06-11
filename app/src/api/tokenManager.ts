// TokenManager — owns the access/refresh token lifecycle.
//
// Guarantees:
//  1. Single-flight refresh *within* a tab: concurrent callers share one
//     in-flight refresh promise (no duplicate network calls).
//  2. Single-flight refresh *across* tabs: the refresh runs inside a cross-tab
//     lock, and the first thing it does is re-read storage. If another tab has
//     already refreshed (the stored access token no longer matches the stale
//     one we set out to replace), we adopt that result instead of calling the
//     network again. This is the "double-checked locking" pattern.
//  3. Propagation: a successful refresh writes to shared storage and broadcasts
//     `tokens-updated`; a failed refresh clears storage and broadcasts
//     `logged-out`. Other tabs react via the channel; this tab notifies its own
//     listeners directly.

import type { AuthChannel, AuthBroadcast } from './broadcast';
import type { CrossTabLock } from './lock';
import type { StoredTokens, TokenStorage } from './storage';
import type { AuthTokenResponse } from './types';

const REFRESH_LOCK = 'event-central.token-refresh';

export class RefreshError extends Error {
  readonly reason: 'no_refresh_token' | 'refresh_failed';

  constructor(
    reason: 'no_refresh_token' | 'refresh_failed',
    options?: { cause?: unknown },
  ) {
    super(`Token refresh failed: ${reason}`);
    this.reason = reason;
    this.name = 'RefreshError';
    if (options?.cause !== undefined) this.cause = options.cause;
  }
}

export type RefreshFn = (refreshToken: string) => Promise<AuthTokenResponse>;

type TokensListener = (tokens: StoredTokens | null) => void;
type LogoutListener = () => void;

export interface TokenManagerOptions {
  storage: TokenStorage;
  lock: CrossTabLock;
  channel: AuthChannel;
  /** Performs the actual network call to exchange a refresh token. */
  refreshFn: RefreshFn;
}

export function mapTokenResponse(res: AuthTokenResponse, previous?: StoredTokens | null): StoredTokens {
  const accessToken = res.access_token;
  if (!accessToken) {
    throw new RefreshError('refresh_failed');
  }
  return {
    accessToken,
    // Some servers omit a rotated refresh token; keep the previous one then.
    refreshToken: res.refresh_token ?? previous?.refreshToken ?? '',
    expiresAt: res.expires_in ? Date.now() + res.expires_in * 1000 : undefined,
    scope: res.scope ?? previous?.scope,
    tokenType: res.token_type ?? previous?.tokenType ?? 'Bearer',
  };
}

export class TokenManager {
  private readonly storage: TokenStorage;
  private readonly lock: CrossTabLock;
  private readonly channel: AuthChannel;
  private readonly refreshFn: RefreshFn;

  private refreshPromise: Promise<StoredTokens> | null = null;
  private tokensListeners = new Set<TokensListener>();
  private logoutListeners = new Set<LogoutListener>();

  constructor(opts: TokenManagerOptions) {
    this.storage = opts.storage;
    this.lock = opts.lock;
    this.channel = opts.channel;
    this.refreshFn = opts.refreshFn;
    this.channel.subscribe(this.handleBroadcast);
  }

  // ---- reads ----

  getTokens(): StoredTokens | null {
    return this.storage.read();
  }

  getAccessToken(): string | null {
    return this.storage.read()?.accessToken ?? null;
  }

  isAuthenticated(): boolean {
    return !!this.storage.read()?.accessToken;
  }

  // ---- writes ----

  /** Persist a freshly issued token pair (e.g. after login). Broadcasts. */
  setTokens(tokens: StoredTokens): void {
    this.storage.write(tokens);
    this.emitTokens(tokens);
    void this.channel.post({ type: 'tokens-updated' });
  }

  /** Clear all auth state (logout / unrecoverable refresh failure). Broadcasts. */
  clear(): void {
    this.storage.clear();
    this.emitTokens(null);
    this.emitLogout();
    void this.channel.post({ type: 'logged-out' });
  }

  // ---- refresh (single-flight, cross-tab) ----

  /**
   * Refresh the access token. `staleAccessToken` is the token the caller tried
   * to use and got rejected; it lets us detect when another tab already
   * refreshed (so we can skip a redundant network call).
   */
  refresh(staleAccessToken?: string | null): Promise<StoredTokens> {
    if (this.refreshPromise) return this.refreshPromise;
    this.refreshPromise = this.lock
      .run(REFRESH_LOCK, () => this.doRefresh(staleAccessToken))
      .finally(() => {
        this.refreshPromise = null;
      });
    return this.refreshPromise;
  }

  private async doRefresh(staleAccessToken?: string | null): Promise<StoredTokens> {
    // Double-check inside the lock: another tab/request may have already done it.
    const current = this.storage.read();
    if (current?.accessToken && staleAccessToken && current.accessToken !== staleAccessToken) {
      this.emitTokens(current);
      return current;
    }

    const refreshToken = current?.refreshToken;
    if (!refreshToken) {
      this.clear();
      throw new RefreshError('no_refresh_token');
    }

    try {
      const res = await this.refreshFn(refreshToken);
      const next = mapTokenResponse(res, current);
      this.setTokens(next);
      return next;
    } catch (err) {
      if (err instanceof RefreshError) {
        this.clear();
        throw err;
      }
      this.clear();
      throw new RefreshError('refresh_failed', { cause: err });
    }
  }

  // ---- subscriptions ----

  onTokensChange(listener: TokensListener): () => void {
    this.tokensListeners.add(listener);
    return () => this.tokensListeners.delete(listener);
  }

  onLogout(listener: LogoutListener): () => void {
    this.logoutListeners.add(listener);
    return () => this.logoutListeners.delete(listener);
  }

  destroy(): void {
    void this.channel.close();
    this.tokensListeners.clear();
    this.logoutListeners.clear();
  }

  // ---- internals ----

  private emitTokens(tokens: StoredTokens | null): void {
    for (const l of this.tokensListeners) l(tokens);
  }

  private emitLogout(): void {
    for (const l of this.logoutListeners) l();
  }

  private handleBroadcast = (message: AuthBroadcast): void => {
    if (message.type === 'tokens-updated') {
      // Another tab refreshed/updated tokens; storage already holds the new
      // values. Re-read and notify our own reactive listeners.
      this.emitTokens(this.storage.read());
    } else if (message.type === 'logged-out') {
      // Another tab logged out. Reflect locally WITHOUT re-broadcasting.
      this.storage.clear();
      this.emitTokens(null);
      this.emitLogout();
    }
  };
}
