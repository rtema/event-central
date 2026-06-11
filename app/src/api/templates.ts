import { api } from "./instance";
import type {
  DocumentTemplate,
  DocumentTemplateResponse,
  DocumentTemplatesListResponse,
  PublicDocumentTemplate,
  PublicDocumentTemplateCreateRequest,
  PublicDocumentTemplateResponse,
  PublicDocumentTemplatesListResponse,
  PublicDocumentTemplateUpdateRequest,
} from "./types";

const base = "/api/v1/document-templates";

export const templatesApi = {
  // --- rendered (private) templates: read-only ---
  list: (): Promise<DocumentTemplate[]> =>
    api
      .get<DocumentTemplatesListResponse>(base)
      .then((r) => r.data.data),

  get: (id: string): Promise<DocumentTemplate> =>
    api
      .get<DocumentTemplateResponse>(`${base}/${id}`)
      .then((r) => r.data.data),

  // --- public templates: read / create / update ---
  listPublic: (): Promise<PublicDocumentTemplate[]> =>
    api
      .get<PublicDocumentTemplatesListResponse>(`${base}/public`)
      .then((r) => r.data.data),

  getPublic: (id: string): Promise<PublicDocumentTemplate> =>
    api
      .get<PublicDocumentTemplateResponse>(`${base}/public/${id}`)
      .then((r) => r.data.data),

  createPublic: (
    body: PublicDocumentTemplateCreateRequest,
  ): Promise<PublicDocumentTemplate> =>
    api
      .post<PublicDocumentTemplateResponse>(`${base}/public`, body)
      .then((r) => r.data.data),

  updatePublic: (
    id: string,
    body: PublicDocumentTemplateUpdateRequest,
  ): Promise<PublicDocumentTemplate> =>
    api
      .post<PublicDocumentTemplateResponse>(`${base}/public/${id}`, body)
      .then((r) => r.data.data),
};
