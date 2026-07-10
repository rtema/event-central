import { api } from "./instance";
import type {
  Event,
  EventResponse,
  EventsListResponse,
  EventSearchParams,
  EventsSearchResponse,
  ListParams,
  OrdersListResponse,
} from "./types";

const base = "/api/v1/events";

export const eventsApi = {
  list: (params?: ListParams) =>
    api.get<EventsListResponse>(base, { params }).then((r) => r.data),

  /** Search/filter events (free-text only, per the spec). */
  search: (params: EventSearchParams): Promise<EventsSearchResponse> => {
    const query: Record<string, string | number> = {};
    if (params.q) query.q = params.q;
    if (params.limit != null) query.limit = params.limit;
    if (params.offset != null) query.offset = params.offset;
    return api
      .get<EventsSearchResponse>(`${base}/search`, { params: query })
      .then((r) => r.data);
  },

  get: (id: string): Promise<Event> =>
    api.get<EventResponse>(`${base}/${id}`).then((r) => r.data.data),

  orders: (id: string, params?: ListParams) =>
    api
      .get<OrdersListResponse>(`${base}/${id}/orders`, { params })
      .then((r) => r.data),
};
