import { createTheme, type MantineColorsTuple } from "@mantine/core";

/**
 * Brand theme for TEMA Technologie Marketing AG.
 *
 * Colours are taken directly from tema.de's CSS custom properties:
 *   --color-primary   #001F47  (deep TEMA navy)
 *   --color-secondary #0F91BD  (TEMA cyan)
 *   --color-accent    #9DB125 / #B8CF2F (TEMA lime)
 *
 * `tema` (navy) is the primary colour for buttons, the login hero and the
 * avatar. `cyan` is available for secondary highlights. The existing `pine`
 * key — used throughout the app for positive/success states — is remapped to
 * the TEMA lime accent so those states stay green and on-brand.
 */
const tema: MantineColorsTuple = [
  "#e7ecf3",
  "#c6d1de",
  "#a5b6ca",
  "#849bb5",
  "#6380a1",
  "#42658c",
  "#214a78",
  "#002f63",
  "#002047",
  "#00112b",
];

const cyan: MantineColorsTuple = [
  "#e2f1f7",
  "#bfe1ed",
  "#9cd1e4",
  "#78c1da",
  "#55b1d0",
  "#32a1c7",
  "#0f91bd",
  "#0c7396",
  "#09546f",
  "#063648",
];

// TEMA lime accent — reused under the existing "pine" key for success states.
const pine: MantineColorsTuple = [
  "#f2f5e0",
  "#e4eac1",
  "#d6dea2",
  "#c8d382",
  "#b9c863",
  "#abbc44",
  "#9db125",
  "#7c8d1e",
  "#5c6a17",
  "#3b4610",
];

export const theme = createTheme({
  primaryColor: "tema",
  primaryShade: { light: 7, dark: 5 },
  colors: { tema, cyan, pine },
  defaultRadius: "md",
  cursorType: "pointer",
  fontFamily:
    '"Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  fontFamilyMonospace:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
  headings: {
    fontFamily:
      '"Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    fontWeight: "650",
    sizes: {
      h1: { fontSize: "1.75rem", lineHeight: "1.2" },
      h2: { fontSize: "1.4rem", lineHeight: "1.25" },
      h3: { fontSize: "1.15rem", lineHeight: "1.3" },
    },
  },
});
