import type {
  UserSalutation,
  UserSearchParams,
  UserTitle,
} from "../../api/types";

const TITLES: UserTitle[] = [
  "dr",
  "dr-ing",
  "prof",
  "prof-dr",
  "prof-dr-ing",
  "phd",
];
const SALUTATIONS: UserSalutation[] = ["mr", "ms", "mx"];

function splitCsv(value: string | null): string[] {
  return value
    ? value
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : [];
}

/** Read the structured filters out of the address bar. */
export function paramsFromUrl(sp: URLSearchParams): UserSearchParams {
  const title = splitCsv(sp.get("title")).filter((t): t is UserTitle =>
    (TITLES as string[]).includes(t),
  );
  const salutation = splitCsv(sp.get("salutation")).filter(
    (s): s is UserSalutation => (SALUTATIONS as string[]).includes(s),
  );
  const q = sp.get("q") ?? undefined;
  const offset = sp.get("offset") ?? undefined;
  return {
    ...(q ? { q } : {}),
    ...(title.length ? { title } : {}),
    ...(salutation.length ? { salutation } : {}),
    ...(offset ? { offset } : {}),
  };
}

/** Serialise filters into a URLSearchParams, dropping empty values. */
export function paramsToUrl(params: UserSearchParams): URLSearchParams {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.title?.length) sp.set("title", params.title.join(","));
  if (params.salutation?.length)
    sp.set("salutation", params.salutation.join(","));
  if (params.offset && params.offset !== "0") sp.set("offset", params.offset);
  return sp;
}

export function hasActiveFilters(params: UserSearchParams): boolean {
  return Boolean(params.q || params.title?.length || params.salutation?.length);
}
