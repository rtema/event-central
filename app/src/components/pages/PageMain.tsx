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
import { useTranslations } from "../utils/useTranslations";
import { AppLayout } from "../ui/AppLayout";
import { AuthProvider } from "../auth/AuthProvider";
import { ProtectedRoute } from "../ui/ProtectedRoute";
import { theme } from "../ui/theme";
import { LoginPage } from "./LoginPage";
import { NotFoundPage } from "./NotFoundPage";
import { PasswordResetPage } from "./PasswordResetPage";
import { UserDetailPage } from "./UserDetailPage";
import { UsersListPage } from "./UsersListPage";

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
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/reset" element={<PasswordResetPage />} />
                  <Route element={<ProtectedRoute />}>
                    <Route element={<AppLayout />}>
                      <Route path="/users" element={<UsersListPage />} />
                      <Route path="/users/:userId" element={<UserDetailPage />} />
                    </Route>
                  </Route>
                  <Route path="/" element={<Navigate to="/users" replace />} />
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
