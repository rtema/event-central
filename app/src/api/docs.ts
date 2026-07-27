import { api } from "./instance";

const base = "/api/v1/docs";

export const docsApi = {
  /**
   * Fetch the raw OpenAPI specification as a YAML string.
   *
   * This is a *secured* endpoint, so we go through the authed `api` instance
   * (which attaches the bearer token and transparently refreshes on 401). We
   * request it as plain text and let the caller parse the YAML — the server
   * returns `application/yaml`, so axios must not try to JSON-parse it.
   */
  spec: (): Promise<string> =>
    api
      .get<string>(`${base}/api-spec.yaml`, {
        responseType: "text",
        // Some proxies default to JSON; make the intent explicit and keep
        // axios from running its JSON transform over the YAML payload.
        headers: { Accept: "application/yaml, text/yaml, text/plain" },
        transformResponse: [(d) => d],
      })
      .then((r) => r.data),
};
