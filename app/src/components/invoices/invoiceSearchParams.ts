import type { InvoiceSearchParams, InvoiceType, Locale } from "../../api/types";

const INVOICE_TYPES: InvoiceType[] = ["invoice", "cancellation"];
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
export function paramsFromUrl(sp: URLSearchParams): InvoiceSearchParams {
  const invoiceType = splitCsv(sp.get("invoiceType")).filter(
    (t): t is InvoiceType => (INVOICE_TYPES as string[]).includes(t),
  );
  const locale = splitCsv(sp.get("locale")).filter((l): l is Locale =>
    (LOCALES as string[]).includes(l),
  );
  const accountingEntity = splitCsv(sp.get("accountingEntity"));
  const q = sp.get("q") ?? undefined;
  const offset = sp.get("offset") ?? undefined;
  return {
    ...(q ? { q } : {}),
    ...(accountingEntity.length ? { accountingEntity } : {}),
    ...(invoiceType.length ? { invoiceType } : {}),
    ...(locale.length ? { locale } : {}),
    ...(offset ? { offset } : {}),
  };
}

/** Serialise filters into a URLSearchParams, dropping empty values. */
export function paramsToUrl(params: InvoiceSearchParams): URLSearchParams {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.accountingEntity?.length)
    sp.set("accountingEntity", params.accountingEntity.join(","));
  if (params.invoiceType?.length)
    sp.set("invoiceType", params.invoiceType.join(","));
  if (params.locale?.length) sp.set("locale", params.locale.join(","));
  if (params.offset && params.offset !== "0") sp.set("offset", params.offset);
  return sp;
}

export function hasActiveFilters(params: InvoiceSearchParams): boolean {
  return Boolean(
    params.q ||
    params.accountingEntity?.length ||
    params.invoiceType?.length ||
    params.locale?.length,
  );
}
