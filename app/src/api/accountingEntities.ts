import { api } from "./instance";
import type { AccountingEntitiesListResponse } from "./types";

export const accountingEntitiesApi = {
  list: (): Promise<string[]> =>
    api
      .get<AccountingEntitiesListResponse>("/api/v1/accounting-entities")
      .then((r) => r.data.data),
};
