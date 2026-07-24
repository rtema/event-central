import { useLingui } from "@lingui/react/macro";
import { Center, Loader } from "@mantine/core";
import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../auth/useAuth";

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();
  const { i18n } = useLingui()

  if (status === "loading") {
    return (
      <Center h="100dvh">
        <Loader />
      </Center>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to={`/${i18n.locale}/auth/login`} replace state={{ from: location }} />;
  }

  return <Outlet />;
}
