import { api } from "./instance";
import type {
  Email,
  EmailAttachment,
  EmailAttachmentsResponse,
  EmailResponse,
  EmailsListResponse,
  EmailSearchParams,
  EmailsSearchResponse,
  ListParams,
} from "./types";

const base = "/api/v1/emails";

export const emailsApi = {
  list: (params?: ListParams): Promise<EmailsListResponse> =>
    api.get<EmailsListResponse>(base, { params }).then((r) => r.data),

  /**
   * Search/filter emails. Array filters are comma-joined to match the spec's
   * `style: form, explode: false` serialization (e.g. `status=failed,retry`).
   */
  search: (params: EmailSearchParams): Promise<EmailsSearchResponse> => {
    const query: Record<string, string | number> = {};
    if (params.q) query.q = params.q;
    if (params.emailTemplate?.length)
      query.emailTemplate = params.emailTemplate.join(",");
    if (params.emailSender?.length)
      query.emailSender = params.emailSender.join(",");
    if (params.status?.length) query.status = params.status.join(",");
    if (params.locale?.length) query.locale = params.locale.join(",");
    if (params.hasAttachments?.length)
      query.hasAttachments = params.hasAttachments.map(String).join(",");
    if (params.limit != null) query.limit = params.limit;
    if (params.offset != null) query.offset = params.offset;
    return api
      .get<EmailsSearchResponse>(`${base}/search`, { params: query })
      .then((r) => r.data);
  },

  get: (id: string): Promise<Email> =>
    api.get<EmailResponse>(`${base}/${id}`).then((r) => r.data.data),

  attachments: (id: string): Promise<EmailAttachment[]> =>
    api
      .get<EmailAttachmentsResponse>(`${base}/${id}/attachments`)
      .then((r) => r.data.data),
};
