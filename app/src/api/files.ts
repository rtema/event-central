import { api } from "./instance";
import type {
  File,
  FileLinkRequest,
  FileLinkResponse,
  FileSearchParams,
  FilesListResponse,
  FilesSearchResponse,
  ListParams,
} from "./types";

const base = "/api/v1/files";

export const filesApi = {
  /** Paginated list of all stored files (max 100 per page). */
  list: (params?: ListParams): Promise<FilesListResponse> =>
    api.get<FilesListResponse>(`${base}/`, { params }).then((r) => r.data),

  /**
   * Search/filter files. Array filters are serialized comma-joined to match the
   * spec's `style: form, explode: false` (e.g. `extension=png,jpg`).
   */
  search: (params: FileSearchParams): Promise<FilesSearchResponse> => {
    const query: Record<string, string | number> = {};
    if (params.q) query.q = params.q;
    if (params.extension?.length) query.extension = params.extension.join(",");
    if (params.type?.length) query.type = params.type.join(",");
    if (params.published?.length)
      query.published = params.published.map(String).join(",");
    if (params.basePath?.length) query.basePath = params.basePath.join(",");
    if (params.limit != null) query.limit = params.limit;
    if (params.offset != null) query.offset = params.offset;
    return api
      .get<FilesSearchResponse>(`${base}/search`, { params: query })
      .then((r) => r.data);
  },

  /**
   * Fetch a single file.
   *
   * API-REVIEW: the spec returns a bare `File` here (no `{ data }` envelope),
   * unlike every sibling endpoint. We accept either shape so nothing breaks
   * whichever way the server actually responds.
   */
  get: (id: string): Promise<File> =>
    api
      .get<File | { data: File }>(`${base}/${id}`)
      .then((r) =>
        r.data && "data" in r.data ? r.data.data : (r.data as File),
      ),

  /** Create a signed, shareable link to view/download the file. */
  link: (id: string, body: FileLinkRequest): Promise<FileLinkResponse> =>
    api.post<FileLinkResponse>(`${base}/${id}/link`, body).then((r) => r.data),
};
