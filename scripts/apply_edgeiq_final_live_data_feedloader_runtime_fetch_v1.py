from pathlib import Path

path = Path('src/edgeiq-os/services/feed-loader/FeedLoader.ts')
text = path.read_text(encoding='utf-8')
old = '''export async function loadRuntimeCsv(path: string): Promise<FeedLoadResult> {
  return loadBundledCsv(path);
}
'''
new = '''export async function loadRuntimeCsv(path: string): Promise<FeedLoadResult> {
  const normalisedPath = path.startsWith("/") ? path : `/${path}`;
  const runtimeCacheKey = `${normalisedPath}::runtime`;

  if (feedCache.has(runtimeCacheKey)) {
    return feedCache.get(runtimeCacheKey)!;
  }

  try {
    const cacheDelimiter = normalisedPath.includes("?") ? "&" : "?";
    const response = await fetch(`${normalisedPath}${cacheDelimiter}updated=${encodeURIComponent(String(Date.now()))}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const text = await response.text();
    if (/^\\s*</.test(text)) {
      throw new Error("HTML response instead of CSV");
    }

    const result: FeedLoadResult = {
      path: normalisedPath,
      rows: parseCsv(text),
      loaded: true,
    };

    feedCache.set(runtimeCacheKey, result);
    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const fallback = loadBundledCsv(normalisedPath);

    if (fallback.loaded) {
      const result: FeedLoadResult = {
        ...fallback,
        path: normalisedPath,
        error: `Runtime fetch failed; using embedded fallback: ${message}`,
      };
      feedCache.set(runtimeCacheKey, result);
      return result;
    }

    const result: FeedLoadResult = {
      path: normalisedPath,
      rows: [],
      loaded: false,
      error: `Runtime CSV fetch failed for ${normalisedPath}: ${message}`,
    };
    feedCache.set(runtimeCacheKey, result);
    return result;
  }
}
'''
if old not in text:
    raise SystemExit('Target loadRuntimeCsv block not found or already changed')
path.write_text(text.replace(old, new), encoding='utf-8')
print('EDGEIQ_FINAL_LIVE_DATA_FEEDLOADER_RUNTIME_FETCH_PATCHED')
