import { api } from "./instance";
import type {
  DocumentTemplate,
  DocumentTemplateFile,
  DocumentTemplateFileResponse,
  DocumentTemplateFilesListResponse,
  DocumentTemplateResponse,
  DocumentTemplatesListResponse,
  ListParams,
  PublicDocumentTemplate,
  PublicDocumentTemplateCreateRequest,
  PublicDocumentTemplateResponse,
  PublicDocumentTemplatesListResponse,
  PublicDocumentTemplateUpdateRequest,
} from "./types";

const base = "/api/v1/document-templates";

/**
 * Fetch a PDF (GET, or POST when `body` is given) and return an object URL for
 * it. The caller owns the URL and must `URL.revokeObjectURL` it.
 */
async function blobUrl(url: string, body?: unknown): Promise<string> {
  const res = body
    ? await api.post<Blob>(url, body, { responseType: "blob" })
    : await api.get<Blob>(url, { responseType: "blob" });
  const blob =
    res.data instanceof Blob
      ? res.data
      : new Blob([res.data as BlobPart], { type: "application/pdf" });
  return URL.createObjectURL(blob);
}

export const documentTemplatesApi = {
  // --- rendered (private) templates: read-only ---
  list: (params?: ListParams): Promise<DocumentTemplatesListResponse> =>
    api
      .get<DocumentTemplatesListResponse>(base, { params })
      .then((r) => r.data),

  get: (id: string): Promise<DocumentTemplate> =>
    api.get<DocumentTemplateResponse>(`${base}/${id}`).then((r) => r.data.data),

  /** Files referenced by a single template. */
  templateFiles: (id: string): Promise<DocumentTemplateFile[]> =>
    api
      .get<DocumentTemplateFilesListResponse>(`${base}/${id}/files`)
      .then((r) => r.data.data),

  /**
   * Render a PDF preview of a template and return an object URL for it.
   *
   * The `/preview` endpoint streams `application/pdf`, so we request a blob and
   * wrap it. The caller owns the returned URL and must `URL.revokeObjectURL` it.
   *
   * API-REVIEW: this is a GET with no body, so only the *saved* template can be
   * previewed and Jinja `{{ variables }}` render empty. A POST variant that
   * accepts draft html/css + sample context would let the editor preview
   * unsaved edits with realistic data — see API-REVIEW.md.
   */
  preview: (id: string): Promise<string> => blobUrl(`${base}/${id}/preview`),

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

  // --- document template files (the template ⇄ file join collection) ---
  listAllFiles: (): Promise<DocumentTemplateFile[]> =>
    api
      .get<DocumentTemplateFilesListResponse>(`${base}/files`)
      .then((r) => r.data.data),

  searchFiles: (q: string): Promise<DocumentTemplateFile[]> =>
    api
      .get<DocumentTemplateFilesListResponse>(`${base}/files/search`, {
        // API-REVIEW: /files/search defines no query parameter. We send `q`
        // (the obvious convention) so this keeps working once the spec adds it.
        params: q ? { q } : undefined,
      })
      .then((r) => r.data.data),

  getFile: (id: string): Promise<DocumentTemplateFile> =>
    api
      .get<DocumentTemplateFileResponse>(`${base}/files/${id}`)
      .then((r) => r.data.data),
};
