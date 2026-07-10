import { api } from "./instance";
import type {
  InvoiceCreateResponse,
  InvoicesListResponse,
  ListParams,
  Order,
  OrderResponse,
  OrderSearchParams,
  OrdersListResponse,
  OrdersSearchResponse,
  Payment,
  PaymentCreateRequest,
  PaymentResponse,
  PaymentsListResponse,
} from "./types";

const base = "/api/v1/orders";

export const ordersApi = {
  list: (params?: ListParams) =>
    api.get<OrdersListResponse>(base, { params }).then((r) => r.data),

  /**
   * Search/filter orders. Array filters are serialized comma-joined to match
   * the spec's `style: form, explode: false` (e.g. `status=open,paid`).
   */
  search: (params: OrderSearchParams): Promise<OrdersSearchResponse> => {
    const query: Record<string, string | number> = {};
    if (params.q) query.q = params.q;
    if (params.status?.length) query.status = params.status.join(",");
    if (params.event?.length) query.event = params.event.join(",");
    if (params.limit != null) query.limit = params.limit;
    if (params.offset != null) query.offset = params.offset;
    return api
      .get<OrdersSearchResponse>(`${base}/search`, { params: query })
      .then((r) => r.data);
  },

  get: (id: string): Promise<Order> =>
    api.get<OrderResponse>(`${base}/${id}`).then((r) => r.data.data),

  /**
   * Cancel an order: the API creates whatever invoices are needed to bring the
   * balance to 0 and returns the created (or last issued) invoice.
   */
  cancel: (id: string): Promise<InvoiceCreateResponse> =>
    api.delete<InvoiceCreateResponse>(`${base}/${id}`).then((r) => r.data),

  payments: (id: string): Promise<Payment[]> =>
    api
      .get<PaymentsListResponse>(`${base}/${id}/payments`)
      .then((r) => r.data.data),

  createPayment: (id: string, body: PaymentCreateRequest): Promise<Payment> =>
    api
      .post<PaymentResponse>(`${base}/${id}/payments`, body)
      .then((r) => r.data.data),

  invoices: (id: string): Promise<InvoicesListResponse> =>
    api.get<InvoicesListResponse>(`${base}/${id}/invoices`).then((r) => r.data),
};
