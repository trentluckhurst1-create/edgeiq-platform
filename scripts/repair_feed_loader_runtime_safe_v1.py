from pathlib import Path

loader = Path("src/edgeiq-os/services/feed-loader/FeedLoader.ts")

loader.write_text(r'''
import { parseCsv } from "./FeedParser";
import type { FeedLoadResult } from "./FeedTypes";

const feedCache = new Map<string, FeedLoadResult>();

const fallbackRows: Record<string, FeedLoadResult> = {};

export function loadBundledCsv(path: string): FeedLoadResult {
  const normalisedPath = path.startsWith("/") ? path : `/${path}`;

  if (feedCache.has(normalisedPath)) {
    return feedCache.get(normalisedPath)!;
  }

  const fallback = fallbackRows[normalisedPath];
  if (fallback) {
    feedCache.set(normalisedPath, fallback);
    return fallback;
  }

  const result: FeedLoadResult = {
    path: normalisedPath,
    rows: [],
    loaded: false,
    error: `Runtime CSV loading required for ${normalisedPath}.`,
  };

  feedCache.set(normalisedPath, result);
  return result;
}

export async function loadRuntimeCsv(path: string): Promise<FeedLoadResult> {
  const normalisedPath = path.startsWith("/") ? path : `/${path}`;

  const response = await fetch(normalisedPath);

  if (!response.ok) {
    const result: FeedLoadResult = {
      path: normalisedPath,
      rows: [],
      loaded: false,
      error: `CSV fetch failed: ${normalisedPath}`,
    };

    feedCache.set(normalisedPath, result);
    return result;
  }

  const text = await response.text();
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

print("[EDGEIQ] FeedLoader changed to runtime-safe loader")
