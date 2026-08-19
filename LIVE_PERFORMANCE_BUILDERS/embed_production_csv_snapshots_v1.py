from pathlib import Path
import json

data_files = {
    "/data/edgeiq_race_shape_story_v1.csv": "edgeiq_race_shape_story_v1.csv",
    "/data/edgeiq_runner_dna_drawer_feed_v2.csv": "edgeiq_runner_dna_drawer_feed_v2.csv",
    "/data/edgeiq_explainability_terminal_feed_v1_2.csv": "edgeiq_explainability_terminal_feed_v1_2.csv",
    "/data/edgeiq_connection_intelligence_v2_1.csv": "edgeiq_connection_intelligence_v2_1.csv",
    "/data/edgeiq_live_track_intelligence_v2_1.csv": "edgeiq_live_track_intelligence_v2_1.csv",
    "/data/edgeiq_live_weather_feed_v1.csv": "edgeiq_live_weather_feed_v1.csv",
    "/data/edgeiq_market_intelligence_v1.csv": "edgeiq_market_intelligence_v1.csv",
    "/data/edgeiq_live_sectional_intelligence_v1.csv": "edgeiq_live_sectional_intelligence_v1.csv",
}

src_data = Path("src/data")
loader = Path("src/edgeiq-os/services/feed-loader/FeedLoader.ts")

entries = []
for public_path, filename in data_files.items():
    csv_path = src_data / filename
    text = csv_path.read_text(encoding="utf-8-sig", errors="ignore")
    entries.append(f'  {json.dumps(public_path)}: {json.dumps(text)},')

loader.write_text(f'''
import {{ parseCsv }} from "./FeedParser";
import type {{ FeedLoadResult }} from "./FeedTypes";

const feedCache = new Map<string, FeedLoadResult>();

const embeddedCsv: Record<string, string> = {{
{chr(10).join(entries)}
}};

export function loadBundledCsv(path: string): FeedLoadResult {{
  const normalisedPath = path.startsWith("/") ? path : `/${{path}}`;

  if (feedCache.has(normalisedPath)) {{
    return feedCache.get(normalisedPath)!;
  }}

  const text = embeddedCsv[normalisedPath];

  if (typeof text !== "string") {{
    const result: FeedLoadResult = {{
      path: normalisedPath,
      rows: [],
      loaded: false,
      error: `Embedded CSV not found for ${{normalisedPath}}.`,
    }};

    feedCache.set(normalisedPath, result);
    return result;
  }}

  const result: FeedLoadResult = {{
    path: normalisedPath,
    rows: parseCsv(text),
    loaded: true,
  }};

  feedCache.set(normalisedPath, result);
  return result;
}}

export async function loadRuntimeCsv(path: string): Promise<FeedLoadResult> {{
  return loadBundledCsv(path);
}}

export function clearFeedCache(): void {{
  feedCache.clear();
}}
'''.lstrip(), encoding="utf-8")

print("[EDGEIQ] FeedLoader embedded production CSV snapshots")
