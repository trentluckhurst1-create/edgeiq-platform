import { parseCsv } from "./FeedParser";
import type { FeedLoadResult } from "./FeedTypes";

const feedCache = new Map<string, FeedLoadResult>();

function normaliseFeedPath(path: string): string {
  return path.startsWith("/") ? path : `/${path}`;
}

function runtimeUrl(path: string): string {
  const delimiter = path.includes("?") ? "&" : "?";
  return `${path}${delimiter}updated=${encodeURIComponent(String(Date.now()))}`;
}

function parseLoadedCsv(path: string, text: string): FeedLoadResult {
  return {
    path,
    rows: parseCsv(text),
    loaded: true,
  };
}

function loadRuntimeCsvSynchronously(path: string): FeedLoadResult {
  if (typeof XMLHttpRequest === "undefined") {
    return {
      path,
      rows: [],
      loaded: false,
      error: `Synchronous runtime CSV loading is unavailable for ${path}.`,
    };
  }

  try {
    const request = new XMLHttpRequest();
    request.open("GET", runtimeUrl(path), false);
    request.setRequestHeader("Cache-Control", "no-store");
    request.send();

    if (request.status < 200 || request.status >= 300) {
      throw new Error(`HTTP ${request.status}`);
    }

    const text = request.responseText;
    if (/^\s*</.test(text)) {
      throw new Error("HTML response instead of CSV");
    }

    return parseLoadedCsv(path, text);
  } catch (error) {
    return {
      path,
      rows: [],
      loaded: false,
      error: `Synchronous runtime CSV load failed for ${path}: ${
        error instanceof Error ? error.message : String(error)
      }`,
    };
  }
}

export function loadBundledCsv(path: string): FeedLoadResult {
  const normalisedPath = normaliseFeedPath(path);

  if (feedCache.has(normalisedPath)) {
    return feedCache.get(normalisedPath)!;
  }

  const result = loadRuntimeCsvSynchronously(normalisedPath);
  feedCache.set(normalisedPath, result);
  return result;
}

export async function loadRuntimeCsv(path: string): Promise<FeedLoadResult> {
  const normalisedPath = normaliseFeedPath(path);

  if (feedCache.has(normalisedPath)) {
    return feedCache.get(normalisedPath)!;
  }

  try {
    const response = await fetch(runtimeUrl(normalisedPath), {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const text = await response.text();
    if (/^\s*</.test(text)) {
      throw new Error("HTML response instead of CSV");
    }

    const result = parseLoadedCsv(normalisedPath, text);
    feedCache.set(normalisedPath, result);
    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const fallback = loadBundledCsv(normalisedPath);

    if (fallback.loaded) {
      return {
        ...fallback,
        error: `Runtime fetch failed; using synchronous runtime fallback: ${message}`,
      };
    }

    const result: FeedLoadResult = {
      path: normalisedPath,
      rows: [],
      loaded: false,
      error: `Runtime CSV fetch failed for ${normalisedPath}: ${message}`,
    };
    feedCache.set(normalisedPath, result);
    return result;
  }
}

export function clearFeedCache(): void {
  feedCache.clear();
}
