/**
 * Types mirroring the Event Central OpenAPI spec (user-management surface).
 * Only the schemas the admin app touches are modelled here.
 */

export type Locale = "de" | "en";

export interface MultiLanguageLabel {
  de?: string;
  en?: string;
}

/** Standard error payload (`#/components/schemas/Error`). */
export interface ApiError {
  code?: number;
  error: string;
  message?: string;
  correlationId?: string;
  details?: Record<string, unknown>;
}

/** OAuth error payload (`#/components/schemas/AuthError`). */
export interface AuthApiError {
  error: string;
  error_description?: string;
  correlationId?: string;
}

// ---- Auth -----------------------------------------------------------------

export type GrantType =
  | "password"
  | "refresh_token"
  | "http://auth0.com/oauth/grant-type/passwordless/otp";

export interface AuthTokenRequest {
  grant_type: GrantType;
  username?: string;
  password?: string;
  otp?: string;
  refresh_token?: string;
  client_id?: string;
  scope?: string;
}

export interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  scope: string;
  expires_in: number;
  token_type: string;
}

export interface AuthUserinfoResponse {
  sub: string;
  email?: string;
  name?: string;
}

export interface AuthPasswordlessStartRequest {
  client_id?: string;
  connection: "email" | "sms";
  email?: string;
  phoneNumber?: string;
  send: "link" | "code";
  authParams: {
    scope: string;
    redirectUri?: string;
    locale: Locale;
  };
}

export interface AuthPasswordResetStartRequest {
  email: string;
  redirectUri: string;
  locale: Locale;
}

export interface AuthPasswordResetConfirmRequest {
  email: string;
  code: string;
  password: string;
}

// ---- Users ----------------------------------------------------------------

export interface User {
  id: string;
  email: string;
  title?: string;
  salutation?: string;
  firstName: string;
  lastName: string;
  createdAt: string;
  deletedAt?: string | null;
}

export interface UserResponse {
  data: User;
}
export interface UsersListResponse {
  data: User[];
}

export interface UsersCreateRequest {
  email: string;
  title?: string;
  salutation?: string;
  firstName: string;
  lastName: string;
}

export type UserUpdateRequest = Partial<UsersCreateRequest>;

export interface UserHistoryItem {
  id: string;
  userId: string;
  createdAt: string;
  changedBy: string;
  newState: {
    email?: string;
    title?: string;
    salutation?: string;
    firstName?: string;
    lastName?: string;
  };
}
export interface UserHistoryResponse {
  data: UserHistoryItem[];
}

export type UserAuthMethod =
  | "api-token"
  | "password"
  | "backup-code"
  | "passwordless"
  | "otp";

export type AuthChangeReason =
  | "user-request"
  | "password-reset"
  | "admin-request"
  | "code-used";

export interface UserAuth {
  id: string;
  userId: string;
  method: UserAuthMethod;
  secret?: string | null;
  createdBy?: string;
  createdReason?: Exclude<AuthChangeReason, "code-used">;
  deletedBy?: string;
  deletedReason?: AuthChangeReason;
  createdAt: string;
  deletedAt?: string | null;
}
/** Note: per the spec these endpoints return the object directly (no `data` wrapper). */
export type UserAuthResponse = UserAuth;
export interface UserAuthListResponse {
  data: UserAuth[];
}

export interface UserAuthCreateRequest {
  method: UserAuthMethod;
  secret?: string | null;
}

export interface UserScope {
  id: string;
  userId: string;
  scope: string;
  createdBy?: string;
  deletedBy?: string;
  createdAt: string;
  deletedAt?: string | null;
}
export interface UserScopesListResponse {
  data: UserScope[];
}
export interface UserScopesUpdateRequest {
  scopes: string[];
}

export interface UserData {
  id: string;
  userId: string;
  createdAt: string;
  changedBy: string;
  data: Record<string, unknown>;
}
export interface UserDataResponse {
  data: UserData;
}

export interface UserDataHistoryItem {
  id: string;
  userId: string;
  createdAt: string;
  changedBy: string;
  newState: Record<string, unknown>;
}
export interface UserDataHistoryResponse {
  data: UserDataHistoryItem[];
}

// ---- Misc -----------------------------------------------------------------

export interface Scope {
  scope: string;
  label?: MultiLanguageLabel;
}
export interface ScopesListResponse {
  data: Scope[];
}
