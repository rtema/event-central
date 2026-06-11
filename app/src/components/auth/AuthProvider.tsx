import {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { logout as apiLogout, fetchUserinfo } from "../../api/auth";
import { onSessionExpired } from "../../api/instance";
import { tokenStore, type TokenSet } from "../../api/tokenStore";
import type { AuthUserinfoResponse } from "../../api/types";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  status: AuthStatus;
  user: AuthUserinfoResponse | null;
  /** Scopes granted to the current access token. */
  scopes: string[];
  hasScope: (scope: string) => boolean;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<TokenSet | null>(() => tokenStore.get());
  const [user, setUser] = useState<AuthUserinfoResponse | null>(null);
  const [status, setStatus] = useState<AuthStatus>(() =>
    tokenStore.hasSession() ? "loading" : "unauthenticated",
  );
  const loadingRef = useRef(false);

  const loadUserinfo = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    try {
      const info = await fetchUserinfo();
      setUser(info);
      setStatus("authenticated");
    } catch {
      // If the failure killed the session, the token store subscription will
      // flip us to "unauthenticated"; otherwise keep showing the app.
      if (!tokenStore.hasSession()) {
        setUser(null);
        setStatus("unauthenticated");
      }
    } finally {
      loadingRef.current = false;
    }
  }, []);

  // Keep local token state in sync with the store (and therefore other tabs).
  useEffect(() => tokenStore.subscribe(setTokens), []);

  // React to a session that can no longer be refreshed.
  useEffect(
    () =>
      onSessionExpired(() => {
        setUser(null);
        setStatus("unauthenticated");
      }),
    [],
  );

  // Load userinfo whenever we gain a session without a known user yet.
  const accessToken = tokens?.accessToken;
  useEffect(() => {
    if (!tokens) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }
    if (!user) {
      setStatus("loading");
      void loadUserinfo();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const scopes = (tokens?.scope ?? "").split(/\s+/).filter(Boolean);
  const value: AuthContextValue = {
    status,
    user,
    scopes,
    hasScope: (s) => scopes.includes(s),
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
