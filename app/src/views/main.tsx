import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";

import { ColorSchemeScript } from "@mantine/core";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { PageMain } from "../components/pages/PageMain";

async function bootstrap() {
  const root = document.getElementById("root");
  if (!root) throw new Error("Root element #root not found");

  createRoot(root).render(
    <StrictMode>
      <ColorSchemeScript defaultColorScheme="auto" />
      <PageMain />
    </StrictMode>,
  );
}

void bootstrap();
