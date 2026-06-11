// The app-wide API singleton: one axios client and one TokenManager, wired
// with the real cross-tab broadcast channel (broadcast-channel) and the
// Web Locks-backed cross-tab refresh lock.
//
// Everything the UI touches goes through `api` (the authed axios instance):
// the request interceptor attaches the bearer token, and a 401 transparently
// triggers a single-flight, cross-tab-serialised refresh + replay.
import { BroadcastChannel } from 'broadcast-channel';
import { config } from '../config';
import { BroadcastChannelAuthChannel } from './broadcast';
import { createApiClient } from './client';

const channel = new BroadcastChannelAuthChannel(
  new BroadcastChannel('event-central.auth') as never,
);

export const { client, tokenManager } = createApiClient({
  baseURL: config.apiBaseUrl,
  clientId: config.clientId,
  scope: config.defaultScope,
  channel,
});

/** The authed axios instance the whole UI/data layer uses. */
export const api = client;

/**
 * Subscribe to "the session can no longer be refreshed" (logout / failed
 * refresh, in this tab or another). Returns an unsubscribe function.
 */
export function onSessionExpired(listener: () => void): () => void {
  return tokenManager.onLogout(listener);
}
