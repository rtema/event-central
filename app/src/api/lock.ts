// Cross-tab mutual exclusion for the token refresh critical section.
//
// Why this matters: when an access token expires, every open tab (and every
// in-flight request) may try to refresh at the same moment. If the refresh
// token rotates on use — the common, safer server behaviour — the first
// refresh invalidates the token the others are about to send, logging the
// user out across tabs. We must guarantee that at most one refresh runs at a
// time across the whole origin, and that the others observe its result.
//
// Primary mechanism: the Web Locks API (`navigator.locks`). It is native,
// origin-scoped, cross-tab, and releases automatically if a tab crashes —
// exactly the guarantees we need. It is widely supported (Chrome 69+,
// Firefox 96+, Safari 15.4+).
//
// Fallback: when Web Locks is unavailable we degrade to an in-tab promise
// chain. Combined with the TokenManager's "re-read storage inside the lock"
// double-check, this still prevents same-tab stampedes and most cross-tab
// races; it cannot fully serialise across tabs, which is an accepted
// limitation on legacy browsers.

export interface CrossTabLock {
  /** Run `fn` while holding the named lock; resolves/rejects with its result. */
  run<T>(name: string, fn: () => Promise<T>): Promise<T>;
}

interface WebLocksNavigator {
  locks?: {
    request: (name: string, callback: () => Promise<unknown>) => Promise<unknown>;
  };
}

export class WebLocksAdapter implements CrossTabLock {
  static isSupported(): boolean {
    const nav = globalThis.navigator as WebLocksNavigator | undefined;
    return typeof nav?.locks?.request === 'function';
  }

  run<T>(name: string, fn: () => Promise<T>): Promise<T> {
    const nav = globalThis.navigator as unknown as WebLocksNavigator;
    return nav.locks!.request(name, () => fn()) as Promise<T>;
  }
}

/** Single-tab fallback: serialises calls per lock name via a promise chain. */
export class InMemoryLock implements CrossTabLock {
  private chains = new Map<string, Promise<unknown>>();

  run<T>(name: string, fn: () => Promise<T>): Promise<T> {
    const previous = this.chains.get(name) ?? Promise.resolve();
    // Each caller waits for the previous holder, then runs. Errors in one
    // holder must not break the chain for the next.
    const result = previous.then(() => fn(), () => fn());
    // Keep the chain alive regardless of success/failure of `result`.
    this.chains.set(
      name,
      result.then(
        () => undefined,
        () => undefined,
      ),
    );
    return result;
  }
}

/** Pick the best available lock for the current environment. */
export function createCrossTabLock(): CrossTabLock {
  return WebLocksAdapter.isSupported() ? new WebLocksAdapter() : new InMemoryLock();
}
