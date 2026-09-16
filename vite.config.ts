import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const isGitHubActions = process.env.GITHUB_ACTIONS === "true";

export default defineConfig({
  base: isGitHubActions ? "/edgeiq-platform/" : "/",
  plugins: [react()],
  build: {
    rollupOptions: {
      output: isGitHubActions
        ? {
            entryFileNames: "assets/edgeiq-app.js",
            chunkFileNames: "assets/edgeiq-[name].js",
            assetFileNames: (assetInfo) =>
              assetInfo.names?.some((name) => name.endsWith(".css"))
                ? "assets/edgeiq-app.css"
                : "assets/[name]-[hash][extname]",
          }
        : undefined,
    },
  },
  server: {
    watch: {
      ignored: [
        "**/public/data/**",
        "**/public/**/*.csv",
        "**/public/**/*.json"
      ],
    },
  },
});
