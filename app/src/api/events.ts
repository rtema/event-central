import { api } from "./instance";
import type {
  Event,
  EventResponse,
  EventsListResponse,
  ListParams,
  OrdersListResponse,
} from "./types";

const base = "/api/v1/events";

export const eventsApi = {
  list: (params?: ListParams) =>
    api.get<EventsListResponse>(base, { params }).then((r) => r.data),

  get: (id: string): Promise<Event> =>
    api.get<EventResponse>(`${base}/${id}`).then((r) => r.data.data),

  orders: (id: string, params?: ListParams) =>
    api
      .get<OrdersListResponse>(`${base}/${id}/orders`, { params })
      .then((r) => r.data),
};
