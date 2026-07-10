import useSWR, { useSWRConfig, type SWRConfiguration } from "swr";
import { scopesApi, usersApi } from "../../api/users";
import { toRequestError } from "../../api/client";
import type { UserSearchParams } from "../../api/types";

/** Cache-key factory so revalidation targets stay consistent across the app. */
export const keys = {
  users: () => ["users"] as const,
  userSearch: (key: string) => ["users-search", key] as const,
  user: (id: string) => ["user", id] as const,
  userHistory: (id: string) => ["user", id, "history"] as const,
  userAuth: (id: string) => ["user", id, "auth"] as const,
  userScopes: (id: string) => ["user", id, "scopes"] as const,
  userData: (id: string) => ["user", id, "data"] as const,
  userDataHistory: (id: string) => ["user", id, "data", "history"] as const,
  scopes: () => ["scopes"] as const,
};

const noRetryOn404: SWRConfiguration = {
  shouldRetryOnError: (err: unknown) => toRequestError(err).status !== 404,
};

export function useUsers() {
  return useSWR(keys.users(), () => usersApi.list());
}

export function useUserSearch(params: UserSearchParams) {
  const key = JSON.stringify({
    q: params.q ?? "",
    title: params.title ?? [],
    salutation: params.salutation ?? [],
    limit: params.limit ?? null,
    offset: params.offset ?? null,
  });
  return useSWR(keys.userSearch(key), () => usersApi.search(params));
}

export function useUser(id: string | undefined) {
  return useSWR(id ? keys.user(id) : null, () => usersApi.get(id!));
}

export function useUserHistory(id: string | undefined) {
  return useSWR(id ? keys.userHistory(id) : null, () => usersApi.history(id!));
}

export function useUserAuth(id: string | undefined) {
  return useSWR(id ? keys.userAuth(id) : null, () => usersApi.listAuth(id!));
}

export function useUserScopes(id: string | undefined) {
  return useSWR(id ? keys.userScopes(id) : null, () =>
    usersApi.listScopes(id!),
  );
}

export function useUserData(id: string | undefined) {
  return useSWR(
    id ? keys.userData(id) : null,
    () => usersApi.getData(id!),
    noRetryOn404,
  );
}

export function useUserDataHistory(id: string | undefined) {
  return useSWR(id ? keys.userDataHistory(id) : null, () =>
    usersApi.dataHistory(id!),
  );
}

export function useScopes() {
  return useSWR(keys.scopes(), () => scopesApi.list());
}

/** Helper to revalidate every cache entry tied to a single user. */
export function useUserMutations(id: string) {
  const { mutate } = useSWRConfig();
  const revalidateUser = () => {
    void mutate(keys.user(id));
    void mutate(keys.userHistory(id));
    void mutate(keys.users());
    void mutate((key) => Array.isArray(key) && key[0] === "users-search");
  };
  return { mutate, revalidateUser };
}
