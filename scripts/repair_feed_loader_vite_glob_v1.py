from pathlib import Path

vite = Path("src/vite-env.d.ts")
existing = vite.read_text(encoding="utf-8") if vite.exists() else ""
if '/// <reference types="vite/client" />' not in existing:
    vite.write_text('/// <reference types="vite/client" />\n' + existing, encoding="utf-8")

loader = Path("src/edgeiq-os/services/feed-loader/FeedLoader.ts")
loader.write_text(r'''
import { parseCsv } from "./FeedParser";
import type { FeedLoadResult } from "./FeedTypes";

const feedCache = new Map<string, FeedLoadResult>();

const bundledFeeds = import.meta.glob("/public/data/*.csv", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export function loadBundledCsv(path: string): FeedLoadResult {
  const normalisedPath = path.startsWith("/") ? path : `/${path}`;

  if (feedCache.has(normalisedPath)) {
    return feedCache.get(normalisedPath)!;
  }

  const bundleKey = `/public${normalisedPath}`;
  const text = bundledFeeds[bundleKey];

  if (typeof text !== "string") {
    const result: FeedLoadResult = {
      path: normalisedPath,
      rows: [],
      loaded: false,
      error: `Bundled feed not found: ${bundleKey}`,
    };

    feedCache.set(normalisedPath, result);
    return result;
  }

  const result: FeedLoadResult = {
    path: normalisedPath,
    rows: parseCsv(text),
    loaded: true,
  };

  feedCache.set(normalisedPath, result);
  return result;
}

export function clearFeedCache(): void {
  feedCache.clear();
}
''', encoding="utf-8")

print("[EDGEIQ] FeedLoader repaired for Vite public data glob")
