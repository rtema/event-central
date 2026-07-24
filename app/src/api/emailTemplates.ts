import { api } from "./instance";
import type {
  EmailTemplate,
  EmailTemplateFile,
  EmailTemplateFileCreateRequest,
  EmailTemplateFileResponse,
  EmailTemplateFilesResponse,
  EmailTemplateFileUpdateRequest,
  EmailTemplatePreview,
  EmailTemplateRequest,
  EmailTemplateResponse,
  EmailTemplatesListResponse,
  EmailTemplateVersion,
  EmailTemplateVersionsResponse,
  ListParams,
} from "./types";

const base = "/api/v1/email-templates";

export const emailTemplatesApi = {
  list: (params?: ListParams): Promise<EmailTemplatesListResponse> =>
    api.get<EmailTemplatesListResponse>(base, { params }).then((r) => r.data),

  get: (id: string): Promise<EmailTemplate> =>
    api.get<EmailTemplateResponse>(`${base}/${id}`).then((r) => r.data.data),

  create: (body: EmailTemplateRequest): Promise<EmailTemplate> =>
    api.post<EmailTemplateResponse>(base, body).then((r) => r.data.data),

  update: (id: string, body: EmailTemplateRequest): Promise<EmailTemplate> =>
    api.patch<EmailTemplateResponse>(`${base}/${id}`, body).then((r) => r.data.data),

  remove: (id: string): Promise<EmailTemplate> =>
    api.delete<EmailTemplateResponse>(`${base}/${id}`).then((r) => r.data.data),

  // --- version history (read-only) ---
  versions: (id: string): Promise<EmailTemplateVersion[]> =>
    api
      .get<EmailTemplateVersionsResponse>(`${base}/${id}/versions`)
      .then((r) => r.data.data),

  /**
   * Render a preview using representative user/event/order/invoice data. Returns
   * the resolved subject, an HTML body, and the version it was rendered from.
   */
  preview: (id: string): Promise<EmailTemplatePreview> =>
    api.get<EmailTemplatePreview>(`${base}/${id}/preview`).then((r) => r.data),

  // --- referenced files ---
  files: (id: string): Promise<EmailTemplateFile[]> =>
    api
      .get<EmailTemplateFilesResponse>(`${base}/${id}/files`)
      .then((r) => r.data.data),

  createFile: (
    id: string,
    body: EmailTemplateFileCreateRequest,
  ): Promise<EmailTemplateFile> =>
    api
      .post<EmailTemplateFileResponse>(`${base}/${id}/files`, body)
      .then((r) => r.data.data),

  updateFile: (
    id: string,
    fileId: string,
    body: EmailTemplateFileUpdateRequest,
  ): Promise<EmailTemplateFile> =>
    api
      .patch<EmailTemplateFileResponse>(`${base}/${id}/files/${fileId}`, body)
      .then((r) => r.data.data),

  removeFile: (id: string, fileId: string): Promise<EmailTemplateFile> =>
    api
      .delete<EmailTemplateFileResponse>(`${base}/${id}/files/${fileId}`)
      .then((r) => r.data.data),
};
