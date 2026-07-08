import type {
  FileExtension,
  FileSearchParams,
  FileType,
} from "../../api/types";

const EXTENSIONS: FileExtension[] = ["png", "jpg", "ttf"];
const TYPES: FileType[] = ["image", "font"];

function splitCsv(value: string | null): string[] {
  return value
    ? value
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : [];
}

/** Read the structured filters out of the address bar. */
export function paramsFromUrl(sp: URLSearchParams): FileSearchParams {
  const extension = splitCsv(sp.get("extension")).filter((e): e is FileExtension =>
    (EXTENSIONS as string[]).includes(e),
  );
  const type = splitCsv(sp.get("type")).filter((t): t is FileType =>
    (TYPES as string[]).includes(t),
  );
  const published = splitCsv(sp.get("published"))
    .filter((p) => p === "true" || p === "false")
    .map((p) => p === "true");
  const basePath = splitCsv(sp.get("basePath"));
  const q = sp.get("q") ?? undefined;
  const offset = sp.get("offset") ?? undefined;
  return {
    ...(q ? { q } : {}),
    ...(extension.length ? { extension } : {}),
    ...(type.length ? { type } : {}),
    ...(published.length ? { published } : {}),
    ...(basePath.length ? { basePath } : {}),
    ...(offset ? { offset } : {}),
  };
}

/** Serialise filters into a URLSearchParams, dropping empty values. */
export function paramsToUrl(params: FileSearchParams): URLSearchParams {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.extension?.length) sp.set("extension", params.extension.join(","));
  if (params.type?.length) sp.set("type", params.type.join(","));
  if (params.published?.length)
    sp.set("published", params.published.map(String).join(","));
  if (params.basePath?.length) sp.set("basePath", params.basePath.join(","));
  if (params.offset && params.offset !== "0") sp.set("offset", params.offset);
  return sp;
}

export function hasActiveFilters(params: FileSearchParams): boolean {
  return Boolean(
    params.q ||
      params.extension?.length ||
      params.type?.length ||
      params.published?.length ||
      params.basePath?.length,
  );
}
