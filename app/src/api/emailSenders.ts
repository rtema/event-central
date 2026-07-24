import { api } from "./instance";
import type {
  EmailSender,
  EmailSenderRequest,
  EmailSenderResponse,
  EmailSendersListResponse,
  EmailSenderSearchParams,
  EmailSendersSearchResponse,
  ListParams,
} from "./types";

const base = "/api/v1/email-senders";

export const emailSendersApi = {
  list: (params?: ListParams): Promise<EmailSendersListResponse> =>
    api.get<EmailSendersListResponse>(base, { params }).then((r) => r.data),

  /**
   * Search senders. The `security` array is comma-joined to match the spec's
   * `style: form, explode: false` serialization (e.g. `security=starttls,ssl`).
   */
  search: (params: EmailSenderSearchParams): Promise<EmailSendersSearchResponse> => {
    const query: Record<string, string | number> = {};
    if (params.q) query.q = params.q;
    if (params.security?.length) query.security = params.security.join(",");
    if (params.limit != null) query.limit = params.limit;
    if (params.offset != null) query.offset = params.offset;
    return api
      .get<EmailSendersSearchResponse>(`${base}/search`, { params: query })
      .then((r) => r.data);
  },

  get: (id: string): Promise<EmailSender> =>
    api.get<EmailSenderResponse>(`${base}/${id}`).then((r) => r.data.data),

  create: (body: EmailSenderRequest): Promise<EmailSender> =>
    api.post<EmailSenderResponse>(base, body).then((r) => r.data.data),

  update: (id: string, body: EmailSenderRequest): Promise<EmailSender> =>
    api.patch<EmailSenderResponse>(`${base}/${id}`, body).then((r) => r.data.data),

  remove: (id: string): Promise<EmailSender> =>
    api.delete<EmailSenderResponse>(`${base}/${id}`).then((r) => r.data.data),
};
