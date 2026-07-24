import useSWR, { useSWRConfig } from "swr";
import { accountingEntitiesApi } from "./accountingEntities";
import { documentTemplatesApi } from "./documentTemplates";
import { emailSendersApi } from "./emailSenders";
import { emailTemplatesApi } from "./emailTemplates";
import { emailsApi } from "./emails";
import { eventsApi } from "./events";
import { filesApi } from "./files";
import { invoicesApi } from "./invoices";
import { ordersApi } from "./orders";
import { paymentsApi } from "./payments";
import { taxesApi } from "./taxes";
import type {
  EmailSearchParams,
  EmailSenderSearchParams,
  EventSearchParams,
  FileSearchParams,
  InvoiceSearchParams,
  ListParams,
  OrderSearchParams,
} from "./types";

/** Cache-key factory shared across the invoicing UI. */
export const invKeys = {
  invoices: (p?: ListParams) =>
    ["invoices", p?.limit ?? null, p?.offset ?? null] as const,
  invoiceSearch: (key: string) => ["invoices-search", key] as const,
  invoice: (id: string) => ["invoice", id] as const,
  invoiceLineItems: (id: string) => ["invoice", id, "line-items"] as const,
  invoiceTaxes: (id: string) => ["invoice", id, "taxes"] as const,

  events: (p?: ListParams) =>
    ["events", p?.limit ?? null, p?.offset ?? null] as const,
  eventSearch: (key: string) => ["events-search", key] as const,
  event: (id: string) => ["event", id] as const,
  eventOrders: (id: string, p?: ListParams) =>
    ["event", id, "orders", p?.limit ?? null, p?.offset ?? null] as const,

  orders: (p?: ListParams) =>
    ["orders", p?.limit ?? null, p?.offset ?? null] as const,
  orderSearch: (key: string) => ["orders-search", key] as const,
  order: (id: string) => ["order", id] as const,
  orderPayments: (id: string) => ["order", id, "payments"] as const,
  orderInvoices: (id: string) => ["order", id, "invoices"] as const,

  payments: (p?: ListParams) =>
    ["payments", p?.limit ?? null, p?.offset ?? null] as const,
  documentTemplates: (p?: ListParams) =>
    ["document-templates", p?.limit ?? null, p?.offset ?? null] as const,
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
  taxes: (p?: ListParams) =>
    ["taxes", p?.limit ?? null, p?.offset ?? null] as const,
  accountingEntities: () => ["accountingEntities"] as const,

  // Email templates.
  emailTemplates: (p?: ListParams) =>
    ["email-templates", p?.limit ?? null, p?.offset ?? null] as const,
  emailTemplate: (id: string) => ["email-template", id] as const,
  emailTemplateFiles: (id: string) => ["email-template", id, "files"] as const,
  emailTemplateVersions: (id: string) =>
    ["email-template", id, "versions"] as const,

  // Email senders.
  emailSenders: (p?: ListParams) =>
    ["email-senders", p?.limit ?? null, p?.offset ?? null] as const,
  emailSenderSearch: (key: string) => ["email-senders-search", key] as const,
  emailSender: (id: string) => ["email-sender", id] as const,

  // Emails.
  emails: (p?: ListParams) =>
    ["emails", p?.limit ?? null, p?.offset ?? null] as const,
  emailSearch: (key: string) => ["emails-search", key] as const,
  email: (id: string) => ["email", id] as const,
  emailAttachments: (id: string) => ["email", id, "attachments"] as const,
};

// ---- Invoices -------------------------------------------------------------

export function useInvoices(params?: ListParams) {
  return useSWR(invKeys.invoices(params), () => invoicesApi.list(params));
}

export function useInvoiceSearch(params: InvoiceSearchParams) {
  const key = JSON.stringify({
    q: params.q ?? "",
    accountingEntity: params.accountingEntity ?? [],
    invoiceType: params.invoiceType ?? [],
    locale: params.locale ?? [],
    limit: params.limit ?? null,
    offset: params.offset ?? null,
  });
  return useSWR(invKeys.invoiceSearch(key), () => invoicesApi.search(params));
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

export function useEventSearch(params: EventSearchParams) {
  const key = JSON.stringify({
    q: params.q ?? "",
    limit: params.limit ?? null,
    offset: params.offset ?? null,
  });
  return useSWR(invKeys.eventSearch(key), () => eventsApi.search(params));
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

export function useOrderSearch(params: OrderSearchParams) {
  const key = JSON.stringify({
    q: params.q ?? "",
    status: params.status ?? [],
    event: params.event ?? [],
    limit: params.limit ?? null,
    offset: params.offset ?? null,
  });
  return useSWR(invKeys.orderSearch(key), () => ordersApi.search(params));
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

export function useDocumentTemplates(params?: ListParams) {
  return useSWR(invKeys.documentTemplates(params), () =>
    documentTemplatesApi.list(params),
  );
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

export function useTaxes(params?: ListParams) {
  return useSWR(invKeys.taxes(params), () => taxesApi.list());
}

export function useAccountingEntities() {
  return useSWR(invKeys.accountingEntities(), () =>
    accountingEntitiesApi.list(),
  );
}

// ---- Email templates ------------------------------------------------------

export function useEmailTemplates(params?: ListParams) {
  return useSWR(invKeys.emailTemplates(params), () =>
    emailTemplatesApi.list(params),
  );
}

export function useEmailTemplate(id: string | undefined) {
  return useSWR(id ? invKeys.emailTemplate(id) : null, () =>
    emailTemplatesApi.get(id!),
  );
}

export function useEmailTemplateFiles(id: string | undefined) {
  return useSWR(id ? invKeys.emailTemplateFiles(id) : null, () =>
    emailTemplatesApi.files(id!),
  );
}

export function useEmailTemplateVersions(id: string | undefined) {
  return useSWR(id ? invKeys.emailTemplateVersions(id) : null, () =>
    emailTemplatesApi.versions(id!),
  );
}

/** Revalidate every template-scoped cache entry after a mutation. */
export function useEmailTemplateMutations(id?: string) {
  const { mutate } = useSWRConfig();
  return {
    mutate,
    revalidateTemplate: () => {
      if (id) {
        void mutate(invKeys.emailTemplate(id));
        void mutate(invKeys.emailTemplateFiles(id));
        void mutate(invKeys.emailTemplateVersions(id));
      }
      void mutate((key) => Array.isArray(key) && key[0] === "email-templates");
    },
  };
}

// ---- Email senders --------------------------------------------------------

export function useEmailSenders(params?: ListParams) {
  return useSWR(invKeys.emailSenders(params), () =>
    emailSendersApi.list(params),
  );
}

export function useEmailSenderSearch(params: EmailSenderSearchParams) {
  const key = JSON.stringify({
    q: params.q ?? "",
    security: params.security ?? [],
    limit: params.limit ?? null,
    offset: params.offset ?? null,
  });
  return useSWR(invKeys.emailSenderSearch(key), () =>
    emailSendersApi.search(params),
  );
}

export function useEmailSender(id: string | undefined) {
  return useSWR(id ? invKeys.emailSender(id) : null, () =>
    emailSendersApi.get(id!),
  );
}

export function useEmailSenderMutations(id?: string) {
  const { mutate } = useSWRConfig();
  return {
    mutate,
    revalidateSenders: () => {
      if (id) void mutate(invKeys.emailSender(id));
      void mutate((key) => Array.isArray(key) && key[0] === "email-senders");
      void mutate(
        (key) => Array.isArray(key) && key[0] === "email-senders-search",
      );
    },
  };
}

// ---- Emails ---------------------------------------------------------------

export function useEmails(params?: ListParams) {
  return useSWR(invKeys.emails(params), () => emailsApi.list(params));
}

export function useEmailSearch(params: EmailSearchParams) {
  const key = JSON.stringify({
    q: params.q ?? "",
    emailTemplate: params.emailTemplate ?? [],
    emailSender: params.emailSender ?? [],
    status: params.status ?? [],
    locale: params.locale ?? [],
    hasAttachments: params.hasAttachments ?? [],
    limit: params.limit ?? null,
    offset: params.offset ?? null,
  });
  return useSWR(invKeys.emailSearch(key), () => emailsApi.search(params));
}

export function useEmail(id: string | undefined) {
  return useSWR(id ? invKeys.email(id) : null, () => emailsApi.get(id!));
}

export function useEmailAttachments(id: string | undefined) {
  return useSWR(id ? invKeys.emailAttachments(id) : null, () =>
    emailsApi.attachments(id!),
  );
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
      void mutate((key) => Array.isArray(key) && key[0] === "orders-search");
      void mutate((key) => Array.isArray(key) && key[0] === "payments");
      void mutate((key) => Array.isArray(key) && key[0] === "invoices-search");
    },
  };
}
