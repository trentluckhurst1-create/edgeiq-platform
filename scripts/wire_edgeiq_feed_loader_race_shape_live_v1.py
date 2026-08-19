from pathlib import Path

feed_loader = Path("src/edgeiq-os/services/feed-loader")
feed_loader.mkdir(parents=True, exist_ok=True)

(feed_loader / "FeedTypes.ts").write_text(r'''
export type FeedRow = Record<string, string>;

export interface FeedLoadResult {
  path: string;
  rows: FeedRow[];
  loaded: boolean;
  error?: string;
}
''', encoding="utf-8")

(feed_loader / "FeedParser.ts").write_text(r'''
import type { FeedRow } from "./FeedTypes";

export function parseCsv(text: string): FeedRow[] {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean);
  if (lines.length <= 1) return [];

  const headers = splitCsvLine(lines[0]).map((item) => item.trim());

  return lines.slice(1).map((line) => {
    const values = splitCsvLine(line);
    const row: FeedRow = {};

    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });

    return row;
  });
}

export function splitCsvLine(line: string): string[] {
  const values: string[] = [];
  let current = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      quoted = !quoted;
      continue;
    }

    if (char === "," && !quoted) {
      values.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  values.push(current);
  return values;
}

export function pick(row: FeedRow | undefined, keys: string[], fallback = ""): string {
  if (!row) return fallback;

  for (const key of keys) {
    const value = row[key];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return String(value).trim();
    }
  }

  return fallback;
}

export function toNumber(value: string | undefined, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
''', encoding="utf-8")

(feed_loader / "FeedLoader.ts").write_text(r'''
import { parseCsv } from "./FeedParser";
import type { FeedLoadResult } from "./FeedTypes";

const feedCache = new Map<string, FeedLoadResult>();

const bundledFeeds = import.meta.glob("/public/data/*.csv", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export function loadBundledCsv(publicPath: string): FeedLoadResult {
  const normalisedPath = publicPath.startsWith("/") ? publicPath : `/${publicPath}`;

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

(feed_loader / "index.ts").write_text(r'''
export * from "./FeedTypes";
export * from "./FeedParser";
export * from "./FeedLoader";
''', encoding="utf-8")

adapters = Path("src/edgeiq-os/services/adapters")

(adapters / "RaceShapeAdapter.ts").write_text(r'''
import { loadBundledCsv, pick, toNumber } from "../feed-loader";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const RACE_SHAPE_SOURCE = "/data/edgeiq_race_shape_story_v1.csv";

export const RaceShapeAdapter: IntelligenceAdapter = {
  key: "race-shape",
  label: "Race Shape",
  buildModuleOutput: () => {
    const feed = loadBundledCsv(RACE_SHAPE_SOURCE);
    const firstRace = feed.rows[0];

    if (!feed.loaded || !firstRace) {
      return {
        key: "race-shape",
        label: "Race Shape",
        category: "PACE",
        status: "ERROR",
        confidence: 0,
        importance: 90,
        evidence: [
          {
            id: "race-shape-feed-error",
            category: "PACE",
            title: "Race Shape feed unavailable",
            summary: feed.error ?? "Race Shape production feed could not be loaded.",
            confidence: 0,
            importance: 90,
            status: "ERROR",
          },
        ],
        feedHealth: {
          key: "race-shape",
          label: "Race Shape",
          status: "ERROR",
          freshness: feed.error ?? "Feed unavailable",
        },
      };
    }

    const tempo = pick(firstRace, ["tempo"], "UNKNOWN");
    const story = pick(firstRace, ["race_shape_story"], "Race shape story pending.");
    const label = pick(firstRace, ["race_shape_label"], "Race Shape");
    const leaders = pick(firstRace, ["likely_leaders"], "No leader profile available");
    const paceAdvantage = pick(firstRace, ["pace_advantage_runner"], "Not identified");
    const pressureRisk = pick(firstRace, ["pressure_risk_runner"], "Not identified");
    const leaderCount = toNumber(firstRace.leader_count, 0);
    const onPaceCount = toNumber(firstRace.on_pace_count, 0);
    const runnerCount = toNumber(firstRace.runner_count, feed.rows.length);

    const pressureConfidence = Math.min(95, 55 + leaderCount * 8 + onPaceCount * 2);

    return {
      key: "race-shape",
      label: "Race Shape",
      category: "PACE",
      status: "READY",
      confidence: pressureConfidence,
      importance: 95,
      evidence: [
        {
          id: "race-shape-story",
          category: "PACE",
          title: `${label} · ${tempo}`,
          summary: story,
          confidence: pressureConfidence,
          importance: 95,
          status: "READY",
        },
        {
          id: "race-shape-leaders",
          category: "PACE",
          title: "Likely leaders",
          summary: leaders,
          confidence: pressureConfidence,
          importance: 85,
          status: "READY",
        },
        {
          id: "race-shape-pressure",
          category: "PACE",
          title: "Map advantage / pressure risk",
          summary: `Map advantage: ${paceAdvantage}. Pressure risk: ${pressureRisk}.`,
          confidence: pressureConfidence,
          importance: 80,
          status: "READY",
        },
      ],
      feedHealth: {
        key: "race-shape",
        label: "Race Shape",
        status: "READY",
        freshness: `Loaded ${feed.rows.length} race shape rows; active sample ${runnerCount} runners`,
      },
    };
  },
};
''', encoding="utf-8")

print("[EDGEIQ_FEED_LOADER_RACE_SHAPE] Feed loader created and Race Shape now reads production CSV")
