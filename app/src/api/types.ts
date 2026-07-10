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

export type UserTitle =
  | "dr"
  | "dr-ing"
  | "prof"
  | "prof-dr"
  | "prof-dr-ing"
  | "phd";

export type UserSalutation = "mr" | "ms" | "mx";

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
  pagination?: Pagination;
}
export interface UserSearchParams {
  q?: string;
  title?: UserTitle[];
  salutation?: UserSalutation[];
  limit?: number;
  offset?: string;
}

export interface UserSearchResponseParams {
  q?: string | null;
  title?: UserTitle[] | null;
  salutation?: UserSalutation[] | null;
}

export interface UsersSearchResponse {
  data: User[];
  pagination?: Pagination;
  search?: UserSearchResponseParams;
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

// ---------------------------------------------------------------------------
// Invoicing domain (invoices, events, orders, payments, templates, taxes)
// Mirrors the Event Central OpenAPI spec.
// ---------------------------------------------------------------------------

export type Currency = "EUR";

/** Pagination metadata returned alongside list endpoints. */
export interface Pagination {
  total?: number;
  limit?: number;
  currentOffset?: number;
}

/** Common query params for paginated list endpoints. */
export interface ListParams {
  limit?: number;
  /** The spec types offset as a string. */
  offset?: string;
}

// ---- Invoices -------------------------------------------------------------

export interface InvoiceSupplier {
  legalName?: string;
  legalRegistration?: string;
  vatId?: string;
  iban?: string;
  bankName?: string;
  line1?: string;
  line2?: string;
  line3?: string;
  city?: string;
  zipCode?: string;
  country?: string;
  contactName?: string;
  contactPhone?: string;
  contactEmail?: string;
}

export interface InvoiceRecipient {
  line1?: string;
  line2?: string;
  line3?: string;
  city?: string;
  zipCode?: string;
  country?: string;
  contactSalutation?: string;
  contactTitle?: string;
  contactFirstname?: string;
  contactLastname?: string;
  contactPhone?: string;
  contactEmail?: string;
  contactCcEmail?: string[];
  purchaseOrderReference?: string;
  vatId?: string;
}

export type InvoiceType = "invoice" | "cancellation";

export interface Invoice {
  id: string;
  orderId?: string;
  documentTemplateId?: string;
  locale?: Locale;
  accountingEntity?: string;
  accountingNumber?: number;
  invoiceNumber?: string;
  invoiceType?: InvoiceType;
  invoiceTypeCode?: string;
  issueDate?: string;
  dueDate?: string;
  currency?: Currency;
  supplier?: InvoiceSupplier;
  recipient?: InvoiceRecipient;
  totalNet?: number;
  totalTax?: number;
  totalGross?: number;
  createdBy?: string;
  createdAt?: string;
}

export interface InvoiceLineItemTicketMetadata {
  externalTicketId?: string;
  externalTicketOptionId?: string;
  externalTicketOptionLabel?: string;
  externalTicketPriceId?: string;
  externalTicketPriceLineId?: string;
  externalTicketPriceLineLabel?: string;
  externalSalesStageId?: string;
  externalSalesStageLabel?: string;
}

export interface InvoiceLineItem {
  id?: string;
  invoiceId?: string;
  taxId?: string;
  position?: number;
  quantity?: number;
  pricePerUnit?: number;
  name?: string;
  ticket?: InvoiceLineItemTicketMetadata;
  taxCategory?: string;
  taxRate?: number;
  taxScheme?: string;
  taxExemptionReason?: string;
  taxExemptionReasonCode?: string;
  totalNet?: number;
  totalTax?: number;
  totalGross?: number;
}

export interface InvoicesListResponse {
  data: Invoice[];
  pagination?: Pagination;
}

export interface InvoiceSearchParams {
  q?: string;
  accountingEntity?: string[];
  invoiceType?: InvoiceType[];
  locale?: Locale[];
  limit?: number;
  offset?: string;
}

export interface InvoiceSearchResponseParams {
  q?: string | null;
  accountingEntity?: string[] | null;
  invoiceType?: InvoiceType[] | null;
  locale?: Locale[] | null;
}

export interface InvoicesSearchResponse {
  data: Invoice[];
  pagination?: Pagination;
  search?: InvoiceSearchResponseParams;
}

export interface InvoiceResponse {
  data: Invoice;
}

export interface InvoiceLineItemsListResponse {
  data: InvoiceLineItem[];
}

export interface InvoiceTaxesListResponse {
  data: Tax[];
}

export type TaxType = "standard" | "exempt-verein";

/** A tax rate entry inside a create request. */
export interface InvoiceCreateTaxRate {
  externalId: string;
  rate: number;
  label: string;
  type?: TaxType;
  taxExemptionReason?: string;
}

/** A line item inside a create request. */
export interface InvoiceCreateLineItem {
  quantity: number;
  pricePerUnit: number;
  externalTaxId: string;
  name: string;
  ticket?: InvoiceLineItemTicketMetadata;
}

/**
 * Font/image as they appear on the immutable `DocumentTemplate` *response*.
 * Note the response keeps `name` for images and has no `weight` — the request
 * shapes below diverge (see `TemplateFontInput` / `TemplateImageInput`).
 */
export interface TemplateFont {
  name: string;
  weight: number;
  file: string;
}

export interface TemplateImage {
  key: string;
  file?: string;
  link?: string;
}

/**
 * Font/image as sent in *request* bodies (public template create/update and
 * invoice create). Each asset may be supplied three ways, in priority order:
 * `fileId` (reference an existing stored file), `file` (base64 upload) or,
 * for images, `link` (public https URL).
 */
export interface TemplateFontInput {
  name?: string;
  weight?: number;
  fileId?: string;
  file?: string;
}

export interface TemplateImageInput {
  key?: string;
  fileId?: string;
  file?: string;
  link?: string;
}

export interface InvoiceTemplateInput {
  templateName?: string;
  html?: string;
  css?: string;
  fonts?: TemplateFont[];
  images?: TemplateImage[];
}

export interface InvoiceCreateRequest {
  externalOrderId?: string;
  locale?: Locale;
  currency?: Currency;
  dueDate?: string;
  accountingEntity?: {
    prefix: string;
    firstInvoiceNumber: number;
    padNumber?: number;
  };
  event?: {
    id?: string;
    label?: string;
    startDt?: string;
    endDt?: string;
  };
  links?: {
    paymentLink?: string;
    orderLink?: string;
  };
  supplier?: InvoiceSupplier;
  recipient?: InvoiceRecipient;
  taxRates?: InvoiceCreateTaxRate[];
  lineItems?: InvoiceCreateLineItem[];
  invoiceTemplate?: InvoiceTemplateInput;
}

export interface InvoiceCreateResponse {
  invoice: Invoice;
  invoiceLines?: InvoiceLineItem[];
  order?: Order;
  event?: Event;
  /** Base64-encoded ZUGFeRD PDF. */
  invoicePdf?: string;
  /** Base64-encoded XRechnung XML. */
  invoiceXml?: string;
}

export type InvoiceFileType = "pdf" | "xrechnung";

export interface InvoiceLinkRequest {
  fileType: InvoiceFileType;
  expiresIn?: number;
}

export interface InvoiceLinkResponse {
  url: string;
  expiresAt?: string;
}

export type InvoiceExportFormat = "xlsx" | "zip";

export interface InvoiceExportRequest {
  accountingEntity?: string;
  format: InvoiceExportFormat;
}

export interface InvoicesExportResponse {
  url: string;
  expiresAt?: string;
}

// ---- Events ---------------------------------------------------------------

export interface Event {
  id?: string;
  label?: MultiLanguageLabel;
  startDt?: string;
  endDt?: string;
  createdAt?: string;
  updatedAt?: string;
  deletedAt?: string | null;
}

export interface EventsListResponse {
  data: Event[];
  pagination?: Pagination;
}

export interface EventSearchParams {
  q?: string;
  limit?: number;
  offset?: string;
}

export interface EventSearchResponseParams {
  q?: string | null;
}

export interface EventsSearchResponse {
  data: Event[];
  pagination?: Pagination;
  search?: EventSearchResponseParams;
}

export interface EventResponse {
  data: Event;
}

// ---- Orders ---------------------------------------------------------------

export type OrderStatus = "open" | "paid" | "cancelled";

export interface Order {
  id: string;
  eventId?: string;
  externalId?: string;
  paymentLink?: string;
  link?: string;
  status?: OrderStatus;
  recipient?: InvoiceRecipient;
  createdAt?: string;
  updatedAt?: string;
  deletedAt?: string | null;
}
export interface OrdersListResponse {
  data: Order[];
  pagination?: Pagination;
}

export interface OrderSearchParams {
  q?: string;
  status?: OrderStatus[];
  /** Comma-separated list of event ids to restrict the result to. */
  event?: string[];
  limit?: number;
  offset?: string;
}

export interface OrderSearchResponseParams {
  q?: string | null;
  status?: OrderStatus[] | null;
  event?: string[] | null;
}

export interface OrdersSearchResponse {
  data: Order[];
  pagination?: Pagination;
  search?: OrderSearchResponseParams;
}

export interface OrderResponse {
  data: Order;
}

// ---- Payments -------------------------------------------------------------

export type PaymentType = "payment" | "refund";

export interface Payment {
  id: string;
  orderId?: string;
  externalId?: string;
  provider?: string;
  method?: string;
  type?: PaymentType;
  status?: string;
  amount?: number;
  currency?: Currency;
  createdBy?: string;
  createdAt?: string;
}

export interface PaymentsListResponse {
  data: Payment[];
  pagination?: Pagination;
}

export interface PaymentResponse {
  data: Payment;
}

export interface PaymentCreateRequest {
  externalId?: string;
  provider?: string;
  method?: string;
  type?: PaymentType;
  status?: string;
  amount?: number;
  currency?: Currency;
}

// ---- Document templates ---------------------------------------------------

export interface DocumentTemplate {
  id: string;
  locale: string;
  publicDocumentTemplateId?: string | null;
  html?: string;
  css?: string;
  fonts?: TemplateFont[];
  images?: TemplateImage[];
  createdAt?: string;
  createdBy?: string;
}

export interface DocumentTemplatesListResponse {
  data: DocumentTemplate[];
  pagination?: Pagination;
}

export interface DocumentTemplateResponse {
  data: DocumentTemplate;
}

export interface PublicDocumentTemplate {
  id: string;
  documentTemplateId?: string;
  locale: string;
  label?: MultiLanguageLabel;
  createdAt?: string;
  updatedAt?: string;
  deletedAt?: string | null;
}

export interface PublicDocumentTemplatesListResponse {
  data: PublicDocumentTemplate[];
  pagination?: Pagination;
}

export interface PublicDocumentTemplateResponse {
  data: PublicDocumentTemplate;
}

export interface PublicDocumentTemplateCreateRequest {
  id: string;
  locale: string;
  html: string;
  css: string;
  fonts: TemplateFontInput[];
  images: TemplateImageInput[];
}

export interface PublicDocumentTemplateUpdateRequest {
  locale: string;
  html: string;
  css: string;
  fonts: TemplateFontInput[];
  images: TemplateImageInput[];
}

// ---- Document template files (template ⇄ file join records) ---------------

export type DocumentTemplateFileType = "image" | "font";

export interface DocumentTemplateFile {
  id: string;
  documentTemplateId: string;
  fileId: string;
  type: DocumentTemplateFileType;
  key?: string;
  fontName?: string;
  fontWeight?: number;
  createdAt?: string;
  createdBy?: string;
}

export interface DocumentTemplateFilesListResponse {
  data: DocumentTemplateFile[];
  pagination?: Pagination;
}

export interface DocumentTemplateFileResponse {
  data: DocumentTemplateFile;
}

// ---- Files ----------------------------------------------------------------
export type FileType = "image" | "font";

export type FileExtension = "png" | "jpg" | "ttf";

export interface File {
  id: string;
  label: MultiLanguageLabel;
  extension: string;
  type: string;
  mime: string;
  published: boolean;
  accessKey: string;
  basePath: string;
  size: number;
  hash: string;
  preview?: string;
  height?: number;
  width?: number;
  meta?: { [key: string]: string };
  createdAt: string;
  createdBy: string;
  deletedAt?: string | null;
  deletedBy?: string | null;
}

export interface FilesListResponse {
  data: File[];
  pagination?: Pagination;
}

export interface FileSearchParams {
  q?: string;
  extension?: FileExtension[];
  type?: FileType[];
  published?: boolean[];
  basePath?: string[];
  limit?: number;
  offset?: string;
}

export interface FileSearchResponseParams {
  q?: string | null;
  extension?: FileExtension[] | null;
  type?: FileType[] | null;
  published?: boolean[] | null;
  basePath?: string[] | null;
}

export interface FilesSearchResponse {
  data: File[];
  pagination?: Pagination;
  search?: FileSearchResponseParams;
}

export interface FileResponse {
  data: File;
}
export interface FileLinkRequest {
  /** Lifetime of the link in seconds (max 31536000). */
  expiresIn?: number;
}

export interface FileLinkResponse {
  url: string;
  expiresAt?: string;
}

// ---- Taxes ----------------------------------------------------------------

export interface Tax {
  id: string;
  externalId?: string;
  rate?: number;
  label?: MultiLanguageLabel;
  type?: TaxType;
  taxExemptionReason?: string;
  createdAt?: string;
  createdBy?: string;
}

export interface TaxesListResponse {
  data: Tax[];
  pagination?: Pagination;
}

// ---- Accounting entities --------------------------------------------------

export interface AccountingEntitiesListResponse {
  data: string[];
}
