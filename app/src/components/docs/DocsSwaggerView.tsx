// Isolated wrapper around `swagger-ui-react`. It is imported lazily from
// `DocsPage` (via `React.lazy`) so the sizable Swagger UI bundle and its global
// stylesheet are only pulled in when someone actually opens the docs page.
import SwaggerUI from "swagger-ui-react";
import swaggerCss from "swagger-ui-react/swagger-ui.css?raw";

interface SwaggerViewProps {
  /** Parsed OpenAPI document (already fetched through the authed client). */
  spec: Record<string, unknown>;
}

export default function DocsSwaggerView({ spec }: SwaggerViewProps) {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: swaggerCss }} />
      <SwaggerUI
        spec={spec}
        docExpansion="list"
        defaultModelsExpandDepth={0}
        tryItOutEnabled={false}
      />
    </>

  );
}