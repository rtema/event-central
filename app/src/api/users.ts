import { api } from "./instance";
import type {
  Scope,
  ScopesListResponse,
  User,
  UserAuth,
  UserAuthCreateRequest,
  UserAuthListResponse,
  UserData,
  UserDataHistoryItem,
  UserDataHistoryResponse,
  UserDataResponse,
  UserHistoryItem,
  UserHistoryResponse,
  UserResponse,
  UsersCreateRequest,
  UserScope,
  UserScopesListResponse,
  UserSearchParams,
  UsersListResponse,
  UsersSearchResponse,
  UserUpdateRequest,
} from "./types";

const base = "/api/v1/users";

export const usersApi = {
  list: () => api.get<UsersListResponse>(base).then((r) => r.data.data),

  /**
   * Search/filter users. Array filters are serialized comma-joined to match the
   * spec's `style: form, explode: false` (e.g. `title=dr,prof`).
   */
  search: (params: UserSearchParams): Promise<UsersSearchResponse> => {
    const query: Record<string, string | number> = {};
    if (params.q) query.q = params.q;
    if (params.title?.length) query.title = params.title.join(",");
    if (params.salutation?.length)
      query.salutation = params.salutation.join(",");
    if (params.limit != null) query.limit = params.limit;
    if (params.offset != null) query.offset = params.offset;
    return api
      .get<UsersSearchResponse>(`${base}/search`, { params: query })
      .then((r) => r.data);
  },

  get: (id: string) =>
    api.get<UserResponse>(`${base}/${id}`).then((r) => r.data.data),

  create: (body: UsersCreateRequest): Promise<User> =>
    api.post<UserResponse>(base, body).then((r) => r.data.data),

  update: (id: string, body: UserUpdateRequest): Promise<User> =>
    api.post<UserResponse>(`${base}/${id}`, body).then((r) => r.data.data),

  remove: (id: string): Promise<User> =>
    api.delete<UserResponse>(`${base}/${id}`).then((r) => r.data.data),

  restore: (id: string): Promise<User> =>
    api.post<UserResponse>(`${base}/${id}/restore`).then((r) => r.data.data),

  history: (id: string): Promise<UserHistoryItem[]> =>
    api
      .get<UserHistoryResponse>(`${base}/${id}/history`)
      .then((r) => r.data.data),

  // --- auth methods (these endpoints return the object directly) ---
  listAuth: (id: string): Promise<UserAuth[]> =>
    api
      .get<UserAuthListResponse>(`${base}/${id}/auth`)
      .then((r) => r.data.data),

  createAuth: (id: string, body: UserAuthCreateRequest): Promise<UserAuth> =>
    api.post<UserAuth>(`${base}/${id}/auth`, body).then((r) => r.data),

  deleteAuth: (id: string, authId: string): Promise<UserAuth> =>
    api.delete<UserAuth>(`${base}/${id}/auth/${authId}`).then((r) => r.data),

  // --- scopes ---
  listScopes: (id: string): Promise<UserScope[]> =>
    api
      .get<UserScopesListResponse>(`${base}/${id}/scopes`)
      .then((r) => r.data.data),

  setScopes: (id: string, scopes: string[]): Promise<UserScope[]> =>
    api
      .post<UserScopesListResponse>(`${base}/${id}/scopes`, { scopes })
      .then((r) => r.data.data),

  // --- arbitrary data ---
  getData: (id: string): Promise<UserData> =>
    api.get<UserDataResponse>(`${base}/${id}/data`).then((r) => r.data.data),

  setData: (id: string, data: Record<string, unknown>): Promise<UserData> =>
    api
      .post<UserDataResponse>(`${base}/${id}/data`, data)
      .then((r) => r.data.data),

  dataHistory: (id: string): Promise<UserDataHistoryItem[]> =>
    api
      .get<UserDataHistoryResponse>(`${base}/${id}/data/history`)
      .then((r) => r.data.data),
};

export const scopesApi = {
  list: (): Promise<Scope[]> =>
    api.get<ScopesListResponse>("/api/v1/scopes").then((r) => r.data.data),
};
