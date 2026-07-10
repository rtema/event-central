import { lingui } from "@lingui/vite-plugin";
import react from "@vitejs/plugin-react";
import fs from "fs";
import { fileURLToPath } from "node:url";
import path from "path";
import { defineConfig, type Plugin } from "vite";

// load .env file
import dotenv from "dotenv";
dotenv.config();

// configure API_BASE_URL, APP_BASE_URL
let apiBaseUrl = process.env.API_BASE_URL;
let appBaseUrl = process.env.APP_BASE_URL;
if (process.env.NODE_ENV === "development") {
  apiBaseUrl = "http://localhost:7435";
  appBaseUrl = "http://localhost:7430";
} else if (process.env.TARGET === "preview") {
  apiBaseUrl = process.env.PREVIEW_API_BASE_URL;
  appBaseUrl = process.env.PREVIEW_APP_BASE_URL;
}
//  else if (process.env.TARGET === "production") {
//   process.env.APP_BASE_URL = process.env.APP_BASE_URL;
// }

// configure prefixes
let APP_PATH_PREFIX = "";
if (process.env.APP_PATH_PREFIX) {
  APP_PATH_PREFIX = process.env.APP_PATH_PREFIX;
}

// assign values
process.env.API_BASE_URL = apiBaseUrl;
process.env.APP_BASE_URL = appBaseUrl;

console.log(`NODE_ENV: ${process.env.NODE_ENV}`);
console.log(`API_BASE_URL: ${process.env.API_BASE_URL}`);
console.log(`APP_BASE_URL: ${process.env.APP_BASE_URL}`);

function copyPlugin({ input, output }: { input: string; output: string }) {
  return {
    name: "copy-files-plugin",
    closeBundle() {
      function copyFiles(srcDir: string, destDir: string) {
        if (!fs.existsSync(destDir)) {
          fs.mkdirSync(destDir, { recursive: true });
        }
        const entries = fs.readdirSync(srcDir, { withFileTypes: true });
        for (const entry of entries) {
          const srcPath = path.join(srcDir, entry.name);
          const destPath = path.join(destDir, entry.name);
          if (entry.isDirectory()) {
            copyFiles(srcPath, destPath);
          } else {
            fs.copyFileSync(srcPath, destPath);
          }
        }
      }

      copyFiles(input, output);
      console.log(`📂 Copied files from ${input} to ${output}`);
    },
  };
}

const devServer = (): Plugin => ({
  name: "dev-server",
  configureServer(server) {
    // server.middlewares.use((req, _res, next) => {
    //   if (req.url?.startsWith("/")) {
    //     console.log(`[DEV-SERVER] Updated: "${req.url}" to "index.html"`);
    //     req.url = "/index.html";
    //   }
    //   // else if (req.url === "/") {
    //   //   console.log(`[DEV-SERVER] Updated: "${req.url}" to "index.html"`);
    //   //   req.url = "/index.html";
    //   // }
    //   next();
    // });
  },
});

// https://vite.dev/config/
export default defineConfig({
  define: {
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
    __API_BASE_URL__: JSON.stringify(process.env.API_BASE_URL),
    __APP_BASE_URL__: JSON.stringify(process.env.APP_BASE_URL),
    __APP_CLIENT_ID__: JSON.stringify(process.env.APP_CLIENT_ID),
    __APP_PATH_PREFIX__: JSON.stringify(APP_PATH_PREFIX),
    __APP_DEFAULT_SCOPE__: JSON.stringify(
      [
        "users:read:all",
        "users:write:all",
        "invoices:read:all",
        "invoices:write:all",
        "events:read:all",
        "orders:read:all",
        "orders:write:all",
        "payments:read:all",
        "payments:write:all",
        "backend:read",
        "backend:write",
      ].join(" "),
    ),
    __LOCAL_STORAGE_ACCESS_TOKEN__: JSON.stringify("access_token"),
    __SESSION_STORAGE_CLIENT_ID__: JSON.stringify("client_id"),
    __LOCAL_STORAGE_REFRESH_TOKEN__: JSON.stringify("refresh_token"),
  },
  css: {
    preprocessorOptions: {
      scss: {
        loadPaths: ["src/styles"],
        additionalData: `@use "_variables.scss" as *; @use "_mantine.scss" as *; `, // optional global variables file
      },
    },
  },
  resolve: {
    alias: [
      {
        find: "@",
        replacement: fileURLToPath(new URL("./src", import.meta.url)),
      },
    ],
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: "./index.html",
      },
    },
  },
  server: {
    port: 7430,
  },
  plugins: [
    devServer(),
    react({
      babel: {
        plugins: ["@lingui/babel-plugin-lingui-macro"],
      },
    }),
    lingui(),
    copyPlugin({
      input: "src/apache-config",
      output: "dist",
    }),
  ],
});
