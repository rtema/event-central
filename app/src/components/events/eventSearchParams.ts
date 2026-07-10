import type { EventSearchParams } from "../../api/types";

/** Read the structured filters out of the address bar. */
export function paramsFromUrl(sp: URLSearchParams): EventSearchParams {
  const q = sp.get("q") ?? undefined;
  const offset = sp.get("offset") ?? undefined;
  return {
    ...(q ? { q } : {}),
    ...(offset ? { offset } : {}),
  };
}

/** Serialise filters into a URLSearchParams, dropping empty values. */
export function paramsToUrl(params: EventSearchParams): URLSearchParams {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.offset && params.offset !== "0") sp.set("offset", params.offset);
  return sp;
}

export function hasActiveFilters(params: EventSearchParams): boolean {
  return Boolean(params.q);
}
