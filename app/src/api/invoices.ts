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
  InvoiceSearchParams,
  InvoicesExportResponse,
  InvoicesListResponse,
  InvoicesSearchResponse,
  Invoice,
  ListParams,
  Tax,
} from "./types";

const base = "/api/v1/invoices";

export const invoicesApi = {
  list: (params?: ListParams) =>
    api.get<InvoicesListResponse>(base, { params }).then((r) => r.data),

  /**
   * Search/filter invoices. Array filters are serialized comma-joined to match
   * the spec's `style: form, explode: false` (e.g. `invoiceType=invoice`).
   */
  search: (params: InvoiceSearchParams): Promise<InvoicesSearchResponse> => {
    const query: Record<string, string | number> = {};
    if (params.q) query.q = params.q;
    if (params.accountingEntity?.length)
      query.accountingEntity = params.accountingEntity.join(",");
    if (params.invoiceType?.length)
      query.invoiceType = params.invoiceType.join(",");
    if (params.locale?.length) query.locale = params.locale.join(",");
    if (params.limit != null) query.limit = params.limit;
    if (params.offset != null) query.offset = params.offset;
    return api
      .get<InvoicesSearchResponse>(`${base}/search`, { params: query })
      .then((r) => r.data);
  },

  get: (id: string): Promise<Invoice> =>
    api.get<InvoiceResponse>(`${base}/${id}`).then((r) => r.data.data),

  create: (body: InvoiceCreateRequest): Promise<InvoiceCreateResponse> =>
    api.post<InvoiceCreateResponse>(base, body).then((r) => r.data),

  lineItems: (id: string): Promise<InvoiceLineItem[]> =>
    api
      .get<InvoiceLineItemsListResponse>(`${base}/${id}/line-items`)
      .then((r) => r.data.data),

  taxes: (id: string): Promise<Tax[]> =>
    api.get<{ data: Tax[] }>(`${base}/${id}/taxes`).then((r) => r.data.data),

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
