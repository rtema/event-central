import { localizedTime } from "./i18n";

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const d = localizedTime(value);
  return d.isValid() ? d.format("lll") : "—";
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = localizedTime(value);
  return d.isValid() ? d.format("ll") : "—";
}

export function formatRelative(value?: string | null): string {
  if (!value) return "—";
  const d = localizedTime(value);
  return d.isValid() ? d.fromNow() : "—";
}
