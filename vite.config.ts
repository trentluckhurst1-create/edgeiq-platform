import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { cpSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";

const runtimePublicDirs = new Set(["data", "performance-intelligence"]);

function copyStaticPublicAssets() {
  return {
    name: "edgeiq-copy-static-public-assets",
    closeBundle() {
      const publicRoot = join(process.cwd(), "public");
      const distRoot = join(process.cwd(), "dist");
      if (!existsSync(publicRoot)) return;
      mkdirSync(distRoot, { recursive: true });
      for (const entry of readdirSync(publicRoot, { withFileTypes: true })) {
        if (runtimePublicDirs.has(entry.name)) continue;
        cpSync(join(publicRoot, entry.name), join(distRoot, entry.name), {
          recursive: true,
          force: true,
        });
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), copyStaticPublicAssets()],
  build: {
    copyPublicDir: false,
  },
  server: {
    proxy: {
      "/api/lab": {
        target: "http://127.0.0.1:8765",
        changeOrigin: false,
      },
    },
    watch: {
      ignored: [
        "**/public/data/**",
        "**/public/**/*.csv",
        "**/public/**/*.json"
      ],
    },
  },
});
