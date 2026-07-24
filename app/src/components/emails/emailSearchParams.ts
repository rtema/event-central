import type { EmailSearchParams, EmailStatus, Locale } from "../../api/types";

const STATUSES: EmailStatus[] = [
  "scheduled",
  "in-progress",
  "delivered",
  "retry",
  "failed",
  "cancelled",
];
const LOCALES: Locale[] = ["de", "en"];

function splitCsv(value: string | null): string[] {
  return value
    ? value
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : [];
}

/** Read the structured filters out of the address bar. */
export function paramsFromUrl(sp: URLSearchParams): EmailSearchParams {
  const status = splitCsv(sp.get("status")).filter((s): s is EmailStatus =>
    (STATUSES as string[]).includes(s),
  );
  const locale = splitCsv(sp.get("locale")).filter((l): l is Locale =>
    (LOCALES as string[]).includes(l),
  );
  const emailTemplate = splitCsv(sp.get("emailTemplate"));
  const emailSender = splitCsv(sp.get("emailSender"));
  const hasAttachments = splitCsv(sp.get("hasAttachments"))
    .filter((v) => v === "true" || v === "false")
    .map((v) => v === "true");
  const q = sp.get("q") ?? undefined;
  const offset = sp.get("offset") ?? undefined;
  return {
    ...(q ? { q } : {}),
    ...(status.length ? { status } : {}),
    ...(locale.length ? { locale } : {}),
    ...(emailTemplate.length ? { emailTemplate } : {}),
    ...(emailSender.length ? { emailSender } : {}),
    ...(hasAttachments.length ? { hasAttachments } : {}),
    ...(offset ? { offset } : {}),
  };
}

/** Serialise filters into URLSearchParams, dropping empty values. */
export function paramsToUrl(params: EmailSearchParams): URLSearchParams {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.status?.length) sp.set("status", params.status.join(","));
  if (params.locale?.length) sp.set("locale", params.locale.join(","));
  if (params.emailTemplate?.length)
    sp.set("emailTemplate", params.emailTemplate.join(","));
  if (params.emailSender?.length)
    sp.set("emailSender", params.emailSender.join(","));
  if (params.hasAttachments?.length)
    sp.set("hasAttachments", params.hasAttachments.map(String).join(","));
  if (params.offset && params.offset !== "0") sp.set("offset", params.offset);
  return sp;
}

export function hasActiveFilters(params: EmailSearchParams): boolean {
  return Boolean(
    params.q ||
      params.status?.length ||
      params.locale?.length ||
      params.emailTemplate?.length ||
      params.emailSender?.length ||
      params.hasAttachments?.length,
  );
}
