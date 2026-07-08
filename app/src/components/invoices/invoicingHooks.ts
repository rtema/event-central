import useSWR, { useSWRConfig } from "swr";
import { eventsApi } from "../../api/events";
import { filesApi } from "../../api/files";
import { invoicesApi } from "../../api/invoices";
import { ordersApi } from "../../api/orders";
import { paymentsApi } from "../../api/payments";
import { taxesApi } from "../../api/taxes";
import { documentTemplatesApi } from "../../api/documentTemplates";
import type { FileSearchParams, ListParams } from "../../api/types";

/** Cache-key factory shared across the invoicing UI. */
export const invKeys = {
  invoices: (p?: ListParams) =>
    ["invoices", p?.limit ?? null, p?.offset ?? null] as const,
  invoice: (id: string) => ["invoice", id] as const,
  invoiceLineItems: (id: string) => ["invoice", id, "line-items"] as const,
  invoiceTaxes: (id: string) => ["invoice", id, "taxes"] as const,

  events: (p?: ListParams) =>
    ["events", p?.limit ?? null, p?.offset ?? null] as const,
  event: (id: string) => ["event", id] as const,
  eventOrders: (id: string, p?: ListParams) =>
    ["event", id, "orders", p?.limit ?? null, p?.offset ?? null] as const,

  orders: (p?: ListParams) =>
    ["orders", p?.limit ?? null, p?.offset ?? null] as const,
  order: (id: string) => ["order", id] as const,
  orderPayments: (id: string) => ["order", id, "payments"] as const,
  orderInvoices: (id: string) => ["order", id, "invoices"] as const,

  payments: (p?: ListParams) =>
    ["payments", p?.limit ?? null, p?.offset ?? null] as const,

  documentTemplates: () => ["document-templates"] as const,
  documentTemplate: (id: string) => ["document-template", id] as const,
  documentTemplateFiles: (id: string) =>
    ["document-template", id, "files"] as const,

  publicDocumentTemplates: () => ["public-document-templates"] as const,
  publicDocumentTemplate: (id: string) =>
    ["public-document-template", id] as const,

  // // Template files (the template ⇄ file join collection).
  // documentTemplateFiles: () => ["document-template-files"] as const,
  // documentTemplateFile: (id: string) => ["document-template-file", id] as const,

  // Stored files.
  files: (p?: ListParams) =>
    ["files", p?.limit ?? null, p?.offset ?? null] as const,
  fileSearch: (key: string) => ["files-search", key] as const,
  file: (id: string) => ["file", id] as const,
  taxes: () => ["taxes"] as const,
};

// ---- Invoices -------------------------------------------------------------

export function useInvoices(params?: ListParams) {
  return useSWR(invKeys.invoices(params), () => invoicesApi.list(params));
}
export function useInvoice(id: string | undefined) {
  return useSWR(id ? invKeys.invoice(id) : null, () => invoicesApi.get(id!));
}
export function useInvoiceLineItems(id: string | undefined) {
  return useSWR(id ? invKeys.invoiceLineItems(id) : null, () =>
    invoicesApi.lineItems(id!),
  );
}
export function useInvoiceTaxes(id: string | undefined) {
  return useSWR(id ? invKeys.invoiceTaxes(id) : null, () =>
    invoicesApi.taxes(id!),
  );
}

// ---- Events ---------------------------------------------------------------

export function useEvents(params?: ListParams) {
  return useSWR(invKeys.events(params), () => eventsApi.list(params));
}
export function useEvent(id: string | undefined) {
  return useSWR(id ? invKeys.event(id) : null, () => eventsApi.get(id!));
}
export function useEventOrders(id: string | undefined, params?: ListParams) {
  return useSWR(id ? invKeys.eventOrders(id, params) : null, () =>
    eventsApi.orders(id!, params),
  );
}

// ---- Orders ---------------------------------------------------------------

export function useOrders(params?: ListParams) {
  return useSWR(invKeys.orders(params), () => ordersApi.list(params));
}
export function useOrder(id: string | undefined) {
  return useSWR(id ? invKeys.order(id) : null, () => ordersApi.get(id!));
}
export function useOrderPayments(id: string | undefined) {
  return useSWR(id ? invKeys.orderPayments(id) : null, () =>
    ordersApi.payments(id!),
  );
}
export function useOrderInvoices(id: string | undefined) {
  return useSWR(id ? invKeys.orderInvoices(id) : null, () =>
    ordersApi.invoices(id!),
  );
}

// ---- Payments -------------------------------------------------------------

export function usePayments(params?: ListParams) {
  return useSWR(invKeys.payments(params), () => paymentsApi.list(params));
}

// ---- Templates ------------------------------------------------------------

export function useDocumentTemplates() {
  return useSWR(invKeys.documentTemplates(), () => documentTemplatesApi.list());
}
export function useDocumentTemplate(id: string | undefined) {
  return useSWR(id ? invKeys.documentTemplate(id) : null, () =>
    documentTemplatesApi.get(id!),
  );
}
export function usePublicDocumentTemplates() {
  return useSWR(invKeys.publicDocumentTemplates(), () =>
    documentTemplatesApi.listPublic(),
  );
}
export function usePublicDocumentTemplate(id: string | undefined) {
  return useSWR(id ? invKeys.publicDocumentTemplate(id) : null, () =>
    documentTemplatesApi.getPublic(id!),
  );
}

// ---- Template files (join records) ----------------------------------------

/** Files referenced by one specific template. */
export function useDocumentTemplateFiles(id: string | undefined) {
  return useSWR(id ? invKeys.documentTemplateFiles(id) : null, () =>
    documentTemplatesApi.templateFiles(id!),
  );
}

// ---- Stored files ---------------------------------------------------------

export function useFiles(params?: ListParams) {
  return useSWR(invKeys.files(params), () => filesApi.list(params));
}
export function useFileSearch(params: FileSearchParams) {
  // Stable cache key from the structured filters.
  const key = JSON.stringify({
    q: params.q ?? "",
    extension: params.extension ?? [],
    type: params.type ?? [],
    published: params.published ?? [],
    basePath: params.basePath ?? [],
    limit: params.limit ?? null,
    offset: params.offset ?? null,
  });
  return useSWR(invKeys.fileSearch(key), () => filesApi.search(params));
}
export function useFile(id: string | undefined) {
  return useSWR(id ? invKeys.file(id) : null, () => filesApi.get(id!));
}

// ---- Misc -----------------------------------------------------------------

export function useTaxes() {
  return useSWR(invKeys.taxes(), () => taxesApi.list());
}

/** Revalidate every order-scoped cache entry after a mutation. */
export function useOrderMutations(id: string) {
  const { mutate } = useSWRConfig();
  return {
    mutate,
    revalidateOrder: () => {
      void mutate(invKeys.order(id));
      void mutate(invKeys.orderPayments(id));
      void mutate(invKeys.orderInvoices(id));
      void mutate((key) => Array.isArray(key) && key[0] === "orders");
      void mutate((key) => Array.isArray(key) && key[0] === "payments");
    },
  };
}
