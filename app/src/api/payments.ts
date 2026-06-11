import { api } from "./instance";
import type { ListParams, PaymentsListResponse } from "./types";

export const paymentsApi = {
  list: (params?: ListParams) =>
    api
      .get<PaymentsListResponse>("/api/v1/payments", { params })
      .then((r) => r.data),
};
