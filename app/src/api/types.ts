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
  contactName?: string;
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

export interface TemplateFont {
  name?: string;
  file?: string;
}
export interface TemplateImage {
  name?: string;
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
  html?: string;
  css?: string;
  fonts?: TemplateFont[];
  images?: TemplateImage[];
}
export interface PublicDocumentTemplateUpdateRequest {
  html?: string;
  css?: string;
  fonts?: TemplateFont[];
  images?: TemplateImage[];
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
