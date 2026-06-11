import { api } from "./instance";
import type { Tax, TaxesListResponse } from "./types";

export const taxesApi = {
  list: (): Promise<Tax[]> =>
    api.get<TaxesListResponse>("/api/v1/taxes").then((r) => r.data.data),
};
