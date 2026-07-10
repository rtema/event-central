// Cross-page persistence for list filters.
//
// The address bar stays the single source of truth while a list is on screen
// (see the `*SearchParams` helpers), but the moment the user leaves a list for
// a detail page that URL is gone. To make "Back to <collection>" return to the
// *previously filtered* list, every list also mirrors its serialized query into
// localStorage under a stable key. Detail pages then read that key back and
// append it to their back-link, so the link literally carries the filter params
// (e.g. `/de/orders?status=open&q=acme`).
//
// localStorage — rather than router state — is used deliberately: it survives a
// full reload on the detail page and a deep-link straight into a detail with no
// history to pop back to.

const PREFIX = "event-central.list-query:";

/** Collections that persist their filter state. */
export type ListKey = "users" | "invoices" | "events" | "orders" | "files";

function storage(): Storage | undefined {
  try {
    return globalThis.localStorage;
  } catch {
    // Access can throw in some privacy modes / sandboxed iframes.
    return undefined;
  }
}

/**
 * Persist (or clear) the current query string for a collection. Pass the same
 * `URLSearchParams` that were written to the address bar.
 */
export function saveListQuery(
  key: ListKey,
  search: URLSearchParams | string,
): void {
  const value = typeof search === "string" ? search : search.toString();
  const store = storage();
  if (!store) return;
  try {
    if (value) store.setItem(PREFIX + key, value);
    else store.removeItem(PREFIX + key);
  } catch {
    // Quota or availability errors are non-fatal: the URL still works.
  }
}

/** Read the last-persisted query string for a collection (without a leading `?`). */
export function loadListQuery(key: ListKey): string {
  const store = storage();
  if (!store) return "";
  try {
    return store.getItem(PREFIX + key) ?? "";
  } catch {
    return "";
  }
}

/**
 * Build a link to a collection's list page that restores the last-used filters.
 * Used by the "Back to <collection>" anchors on detail pages.
 */
export function listLinkWithFilters(basePath: string, key: ListKey): string {
  const query = loadListQuery(key);
  return query ? `${basePath}?${query}` : basePath;
}
