import { i18n } from "@lingui/core";
import type { MultiLanguageLabel } from "../../api/types";

/** Format a monetary amount in the active locale. */
export function formatMoney(
  value?: number | null,
  currency: string = "EUR",
): string {
  if (value == null || Number.isNaN(value)) return "—";
  try {
    return new Intl.NumberFormat(i18n.locale || "en", {
      style: "currency",
      currency,
    }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

/** Format a plain number in the active locale. */
export function formatNumber(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  try {
    return new Intl.NumberFormat(i18n.locale || "en").format(value);
  } catch {
    return String(value);
  }
}

/** Pick the best string from a multi-language label for the active locale. */
export function localizedLabel(label?: MultiLanguageLabel | null): string {
  if (!label) return "—";
  const locale = (i18n.locale || "en") as keyof MultiLanguageLabel;
  return label[locale] || label.en || label.de || "—";
}

/**
 * Decode a base64 payload into a Blob and trigger a browser download. Used for
 * the inline PDF/XML returned by the invoice create endpoint.
 */
export function downloadBase64(
  base64: string,
  fileName: string,
  mimeType: string,
): void {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Read a File into a bare base64 string (no data: prefix). */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result);
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

/** Human-readable file size (1024-based) in the active locale. */
export function formatBytes(bytes?: number | null): string {
  if (bytes == null || Number.isNaN(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${formatNumber(Math.round(value * 10) / 10)} ${units[unit]}`;
}
