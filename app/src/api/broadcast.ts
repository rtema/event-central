// Cross-tab messaging for auth state.
//
// We use the `broadcast-channel` package rather than the raw BroadcastChannel
// Web API because it is battle-tested, ships a localStorage/IndexedDB fallback
// for environments without native support, and — critically — does NOT echo a
// message back to the instance that posted it. That self-exclusion lets the
// posting tab update its own in-memory state directly while every other tab
// reacts to the broadcast, with no double-application.
//
// The interface is injectable so tests can drive deterministic fakes.

export type AuthBroadcast =
  | { type: 'tokens-updated' }
  | { type: 'logged-out' };

export interface AuthChannel {
  post(message: AuthBroadcast): Promise<void> | void;
  subscribe(handler: (message: AuthBroadcast) => void): void;
  close(): Promise<void> | void;
}

/** Minimal shape we rely on from `broadcast-channel` (and the native API). */
export interface RawChannel<T> {
  postMessage(message: T): Promise<void> | void;
  onmessage: ((message: T) => void) | null;
  close(): Promise<void> | void;
}

/**
 * Adapter over any BroadcastChannel-like object. In the browser, construct it
 * with `new BroadcastChannelAuthChannel(new BroadcastChannel('event-central.auth'))`
 * from the `broadcast-channel` package (see createAuthChannel in client.ts).
 */
export class BroadcastChannelAuthChannel implements AuthChannel {
  private readonly channel: RawChannel<AuthBroadcast>;

  constructor(channel: RawChannel<AuthBroadcast>) {
    this.channel = channel;
  }

  post(message: AuthBroadcast): Promise<void> | void {
    return this.channel.postMessage(message);
  }

  subscribe(handler: (message: AuthBroadcast) => void): void {
    this.channel.onmessage = handler;
  }

  close(): Promise<void> | void {
    return this.channel.close();
  }
}

/** No-op channel for environments where cross-tab sync is irrelevant. */
export class NoopAuthChannel implements AuthChannel {
  post(): void {}
  subscribe(): void {}
  close(): void {}
}
