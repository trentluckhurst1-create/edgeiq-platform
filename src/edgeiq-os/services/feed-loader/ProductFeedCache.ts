export type JsonFeedLoadOptions<T> = {
  force?: boolean;
  cacheKey?: string;
  maxBytes?: number;
  normalise?: (payload: unknown) => T;
};

type CacheEntry<T> = {
  value: T | null;
  pending: Promise<T> | null;
  loadedAt: number | null;
  hitCount: number;
  missCount: number;
};

const jsonCache = new Map<string, CacheEntry<unknown>>();

function entryFor<T>(key: string): CacheEntry<T> {
  const existing = jsonCache.get(key) as CacheEntry<T> | undefined;
  if (existing) return existing;
  const created: CacheEntry<T> = {
    value: null,
    pending: null,
    loadedAt: null,
    hitCount: 0,
    missCount: 0,
  };
  jsonCache.set(key, created as CacheEntry<unknown>);
  return created;
}

function requestUrl(url: string): string {
  return `${url}${url.includes("?") ? "&" : "?"}updated=${encodeURIComponent(String(Date.now()))}`;
}

export async function loadJsonFeed<T>(url: string, options: JsonFeedLoadOptions<T> = {}): Promise<T> {
  const key = options.cacheKey ?? url;
  const entry = entryFor<T>(key);

  if (!options.force && entry.value) {
    entry.hitCount += 1;
    return entry.value;
  }

  if (entry.pending) {
    entry.hitCount += 1;
    return entry.pending;
  }

  entry.missCount += 1;
  entry.pending = fetch(requestUrl(url), { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`${url} failed with ${response.status}`);
      const text = await response.text();
      if (options.maxBytes && text.length > options.maxBytes) {
        console.warn("EDGEiQ rejected oversized JSON feed", url, text.length);
        throw new Error(`${url} exceeded JSON feed size guard`);
      }
      const parsed = JSON.parse(text) as unknown;
      return options.normalise ? options.normalise(parsed) : (parsed as T);
    })
    .then((value) => {
      entry.value = value;
      entry.loadedAt = Date.now();
      return value;
    })
    .finally(() => {
      entry.pending = null;
    });

  return entry.pending;
}

export function clearJsonFeedCache(cacheKey?: string): void {
  if (cacheKey) {
    jsonCache.delete(cacheKey);
    return;
  }
  jsonCache.clear();
}

export function getJsonFeedCacheStats(): Array<{ key: string; loaded: boolean; loadedAt: number | null; hitCount: number; missCount: number }> {
  return Array.from(jsonCache.entries()).map(([key, entry]) => ({
    key,
    loaded: Boolean(entry.value),
    loadedAt: entry.loadedAt,
    hitCount: entry.hitCount,
    missCount: entry.missCount,
  }));
}
