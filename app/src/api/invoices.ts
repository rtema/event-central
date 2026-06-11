import { api } from "./instance";
import type {
  InvoiceCreateRequest,
  InvoiceCreateResponse,
  InvoiceExportRequest,
  InvoiceLineItem,
  InvoiceLineItemsListResponse,
  InvoiceLinkRequest,
  InvoiceLinkResponse,
  InvoiceResponse,
  InvoicesExportResponse,
  InvoicesListResponse,
  Invoice,
  ListParams,
  Tax,
} from "./types";

const base = "/api/v1/invoices";

export const invoicesApi = {
  list: (params?: ListParams) =>
    api
      .get<InvoicesListResponse>(base, { params })
      .then((r) => r.data),

  get: (id: string): Promise<Invoice> =>
    api.get<InvoiceResponse>(`${base}/${id}`).then((r) => r.data.data),

  create: (body: InvoiceCreateRequest): Promise<InvoiceCreateResponse> =>
    api.post<InvoiceCreateResponse>(base, body).then((r) => r.data),

  lineItems: (id: string): Promise<InvoiceLineItem[]> =>
    api
      .get<InvoiceLineItemsListResponse>(`${base}/${id}/line-items`)
      .then((r) => r.data.data),

  taxes: (id: string): Promise<Tax[]> =>
    api
      .get<{ data: Tax[] }>(`${base}/${id}/taxes`)
      .then((r) => r.data.data),

  /** Create a signed, shareable download link for a generated document. */
  link: (id: string, body: InvoiceLinkRequest): Promise<InvoiceLinkResponse> =>
    api
      .post<InvoiceLinkResponse>(`${base}/${id}/link`, body)
      .then((r) => r.data),

  export: (body: InvoiceExportRequest): Promise<InvoicesExportResponse> =>
    api
      .post<InvoicesExportResponse>(`${base}/export`, body)
      .then((r) => r.data),
};
