import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const isGitHubActions = process.env.GITHUB_ACTIONS === "true";

export default defineConfig({
  base: isGitHubActions ? "/edgeiq-platform/" : "/",
  plugins: [react()],
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
