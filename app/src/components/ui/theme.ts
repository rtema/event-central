import { createTheme, type MantineColorsTuple } from "@mantine/core";

/**
 * Design note: this is an internal administration console for a German B2B
 * e-invoicing platform. The identity leans on a calm "pine" green — a ledger /
 * trust colour that deliberately avoids the default Mantine blue and the
 * over-used terracotta/acid-green of generated UIs. Everything else stays
 * quiet and dense so the data is the hero.
 */
const pine: MantineColorsTuple = [
  "#eafaf2",
  "#d6f0e3",
  "#aee0c6",
  "#82d0a7",
  "#5dc28d",
  "#45b97c",
  "#36b573",
  "#259e61",
  "#178d55",
  "#007a47",
];

export const theme = createTheme({
  primaryColor: "pine",
  primaryShade: { light: 7, dark: 5 },
  colors: { pine },
  defaultRadius: "md",
  cursorType: "pointer",
  fontFamily:
    'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  fontFamilyMonospace:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
  headings: {
    fontWeight: "650",
    sizes: {
      h1: { fontSize: "1.75rem", lineHeight: "1.2" },
      h2: { fontSize: "1.4rem", lineHeight: "1.25" },
      h3: { fontSize: "1.15rem", lineHeight: "1.3" },
    },
  },
});
