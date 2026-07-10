import type { OrderSearchParams, OrderStatus } from "../../api/types";

const STATUSES: OrderStatus[] = ["open", "paid", "cancelled"];

function splitCsv(value: string | null): string[] {
  return value
    ? value
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : [];
}

/** Read the structured filters out of the address bar. */
export function paramsFromUrl(sp: URLSearchParams): OrderSearchParams {
  const status = splitCsv(sp.get("status")).filter((s): s is OrderStatus =>
    (STATUSES as string[]).includes(s),
  );
  const event = splitCsv(sp.get("event"));
  const q = sp.get("q") ?? undefined;
  const offset = sp.get("offset") ?? undefined;
  return {
    ...(q ? { q } : {}),
    ...(status.length ? { status } : {}),
    ...(event.length ? { event } : {}),
    ...(offset ? { offset } : {}),
  };
}

/** Serialise filters into a URLSearchParams, dropping empty values. */
export function paramsToUrl(params: OrderSearchParams): URLSearchParams {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.status?.length) sp.set("status", params.status.join(","));
  if (params.event?.length) sp.set("event", params.event.join(","));
  if (params.offset && params.offset !== "0") sp.set("offset", params.offset);
  return sp;
}

export function hasActiveFilters(params: OrderSearchParams): boolean {
  return Boolean(params.q || params.status?.length || params.event?.length);
}
