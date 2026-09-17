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
            // Production assets MUST be content hashed. Fixed edgeiq-app.js/css names
            // allowed browsers/CDNs to keep serving an older EDGEiQ UI after a successful
            // Pages deployment.
            entryFileNames: "assets/edgeiq-app-[hash].js",
            chunkFileNames: "assets/edgeiq-[name]-[hash].js",
            assetFileNames: "assets/edgeiq-[name]-[hash][extname]",
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
