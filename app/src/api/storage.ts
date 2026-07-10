// Token storage abstraction.
//
// localStorage is the cross-tab source of truth: it is shared across all tabs
// of the same origin, survives reloads, and emits `storage` events to other
// tabs. The TokenManager layers an explicit BroadcastChannel on top for
// low-latency, same-instance-safe notifications, but persistence lives here.
//
// The interface is injectable so the manager can be unit-tested in Node with
// an in-memory implementation (no jsdom/localStorage required).

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
  /** Epoch millis at which the access token expires (best-effort). */
  expiresAt?: number;
  scope?: string;
  tokenType?: string;
}

export interface TokenStorage {
  read(): StoredTokens | null;
  write(tokens: StoredTokens): void;
  clear(): void;
}

const STORAGE_KEY = "event-central.auth.tokens";

/** localStorage-backed implementation used in the browser. */
export class LocalTokenStorage implements TokenStorage {
  private readonly key: string;

  constructor(key: string = STORAGE_KEY) {
    this.key = key;
  }

  read(): StoredTokens | null {
    try {
      const raw = globalThis.localStorage?.getItem(this.key);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as StoredTokens;
      if (!parsed?.accessToken || !parsed?.refreshToken) return null;
      return parsed;
    } catch {
      return null;
    }
  }

  write(tokens: StoredTokens): void {
    try {
      globalThis.localStorage?.setItem(this.key, JSON.stringify(tokens));
    } catch {
      // Quota or privacy-mode errors are non-fatal; in-memory state still holds.
    }
  }

  clear(): void {
    try {
      globalThis.localStorage?.removeItem(this.key);
    } catch {
      // ignore
    }
  }
}

/** In-memory implementation for tests and SSR-safe fallbacks. */
export class MemoryTokenStorage implements TokenStorage {
  private value: StoredTokens | null = null;
  read(): StoredTokens | null {
    return this.value;
  }
  write(tokens: StoredTokens): void {
    this.value = tokens;
  }
  clear(): void {
    this.value = null;
  }
}
