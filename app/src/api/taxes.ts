import { api } from "./instance";
import type { ListParams, TaxesListResponse } from "./types";

const base = "/api/v1/taxes";

export const taxesApi = {
  list: (params?: ListParams): Promise<TaxesListResponse> =>
    api.get<TaxesListResponse>(base, { params }).then((r) => r.data),
};
