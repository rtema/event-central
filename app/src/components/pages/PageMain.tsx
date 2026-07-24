import { i18n } from "@lingui/core";
import { I18nProvider } from "@lingui/react";
import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router";
import { SWRConfig } from "swr";
import { AuthProvider } from "../auth/AuthProvider";
import { Login } from "../auth/Login";
import { PasswordReset } from "../auth/PasswordReset";
import { DocumentTemplateDetail } from "../document-templates/DocumentTemplateDetail";
import { DocumentTemplatesList } from "../document-templates/DocumentTemplatesList";
import { PublicDocumentTemplateEditor } from "../document-templates/PublicDocumentTemplateEditor";
import { EmailDetail } from "../emails/EmailDetail";
import { EmailsList } from "../emails/EmailsList";
import { EmailSendersList } from "../email-senders/EmailSendersList";
import { EmailTemplateDetail } from "../email-templates/EmailTemplateDetail";
import { EmailTemplatesList } from "../email-templates/EmailTemplatesList";
import { EventDetail } from "../events/EventDetail";
import { EventsList } from "../events/EventsList";
import { FilesList } from "../files/FilesList";
import { FileDetail } from "../files/FileDetail";
import { InvoiceCreate } from "../invoices/InvoiceCreate";
import { InvoiceDetail } from "../invoices/InvoiceDetail";
import { InvoicesList } from "../invoices/InvoicesList";
import { OrderDetail } from "../orders/OrderDetail";
import { OrdersList } from "../orders/OrdersList";
import { PaymentsList } from "../payments/PaymentsList";
import { TaxesList } from "../taxes/TaxesList";
import { AppLayout } from "../ui/AppLayout";
import { ProtectedRoute } from "../ui/ProtectedRoute";
import { theme } from "../ui/theme";
import { UserDetail } from "../users/UserDetail";
import { UsersList } from "../users/UsersList";
import { useTranslations } from "../utils/useTranslations";
import { NotFoundPage } from "./NotFoundPage";
import { PageHome } from "./PageHome";

export function PageMain() {
  // Load the correct translations
  useTranslations();

  return (
    <I18nProvider i18n={i18n}>
      <MantineProvider theme={theme} defaultColorScheme="auto">
        <Notifications position="top-right" />
        <SWRConfig
          value={{
            revalidateOnFocus: true,
            shouldRetryOnError: true,
            errorRetryCount: 2,
            dedupingInterval: 2000,
          }}
        >
          <BrowserRouter>
            <AuthProvider>
              <ModalsProvider>
                <Routes>
                  <Route path="/:lang">
                    <Route path="login" element={<Login />} />
                    <Route path="reset" element={<PasswordReset />} />
                    <Route element={<ProtectedRoute />}>
                      <Route element={<AppLayout />}>
                        <Route path="home" element={<PageHome />} />
                        <Route path="users" element={<UsersList />} />
                        <Route path="users/:userId" element={<UserDetail />} />

                        <Route path="invoices" element={<InvoicesList />} />
                        <Route path="invoices/new" element={<InvoiceCreate />} />
                        <Route path="invoices/:invoiceId" element={<InvoiceDetail />} />

                        <Route path="events" element={<EventsList />} />
                        <Route path="events/:eventId" element={<EventDetail />} />

                        <Route path="orders" element={<OrdersList />} />
                        <Route path="orders/:orderId" element={<OrderDetail />} />

                        <Route path="payments" element={<PaymentsList />} />

                        <Route path="taxes" element={<TaxesList />} />

                        <Route path="document-templates" element={<DocumentTemplatesList />} />
                        <Route
                          path="document-templates/public/:templateId"
                          element={<PublicDocumentTemplateEditor />}
                        />
                        <Route
                          path="document-templates/rendered/:templateId"
                          element={<DocumentTemplateDetail />}
                        />
                        <Route path="files" element={<FilesList />} />
                        <Route
                          path="files/:fileId"
                          element={<FileDetail />}
                        />

                        <Route path="emails" element={<EmailsList />} />
                        <Route path="emails/:emailId" element={<EmailDetail />} />

                        <Route
                          path="email-templates"
                          element={<EmailTemplatesList />}
                        />
                        <Route
                          path="email-templates/:templateId"
                          element={<EmailTemplateDetail />}
                        />

                        <Route
                          path="email-senders"
                          element={<EmailSendersList />}
                        />
                      </Route>
                    </Route>
                  </Route>

                  <Route path="/" element={<Navigate to="/de/home" replace />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </ModalsProvider>
            </AuthProvider>
          </BrowserRouter>
        </SWRConfig>
      </MantineProvider>
    </I18nProvider>
  );
}
