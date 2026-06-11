import { api } from "./instance";
import type {
  InvoiceCreateResponse,
  InvoicesListResponse,
  ListParams,
  Order,
  OrderResponse,
  OrdersListResponse,
  Payment,
  PaymentCreateRequest,
  PaymentResponse,
  PaymentsListResponse,
} from "./types";

const base = "/api/v1/orders";

export const ordersApi = {
  list: (params?: ListParams) =>
    api.get<OrdersListResponse>(base, { params }).then((r) => r.data),

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
