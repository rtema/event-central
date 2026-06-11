import useSWR, { useSWRConfig } from "swr";
import { eventsApi } from "../../api/events";
import { invoicesApi } from "../../api/invoices";
import { ordersApi } from "../../api/orders";
import { paymentsApi } from "../../api/payments";
import { taxesApi } from "../../api/taxes";
import { templatesApi } from "../../api/templates";
import type { ListParams } from "../../api/types";

/** Cache-key factory shared across the invoicing UI. */
export const invKeys = {
  invoices: (p?: ListParams) => ["invoices", p?.limit ?? null, p?.offset ?? null] as const,
  invoice: (id: string) => ["invoice", id] as const,
  invoiceLineItems: (id: string) => ["invoice", id, "line-items"] as const,
  invoiceTaxes: (id: string) => ["invoice", id, "taxes"] as const,

  events: (p?: ListParams) => ["events", p?.limit ?? null, p?.offset ?? null] as const,
  event: (id: string) => ["event", id] as const,
  eventOrders: (id: string, p?: ListParams) =>
    ["event", id, "orders", p?.limit ?? null, p?.offset ?? null] as const,

  orders: (p?: ListParams) => ["orders", p?.limit ?? null, p?.offset ?? null] as const,
  order: (id: string) => ["order", id] as const,
  orderPayments: (id: string) => ["order", id, "payments"] as const,
  orderInvoices: (id: string) => ["order", id, "invoices"] as const,

  payments: (p?: ListParams) => ["payments", p?.limit ?? null, p?.offset ?? null] as const,

  templates: () => ["document-templates"] as const,
  template: (id: string) => ["document-template", id] as const,
  publicTemplates: () => ["public-document-templates"] as const,
  publicTemplate: (id: string) => ["public-document-template", id] as const,

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
  return useSWR(invKeys.templates(), () => templatesApi.list());
}
export function useDocumentTemplate(id: string | undefined) {
  return useSWR(id ? invKeys.template(id) : null, () =>
    templatesApi.get(id!),
  );
}
export function usePublicTemplates() {
  return useSWR(invKeys.publicTemplates(), () => templatesApi.listPublic());
}
export function usePublicTemplate(id: string | undefined) {
  return useSWR(id ? invKeys.publicTemplate(id) : null, () =>
    templatesApi.getPublic(id!),
  );
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
