from pathlib import Path
import re

# ------------------------------------------------------------------
# 1. EdgeiqCommandWorkspace.tsx
# ------------------------------------------------------------------

cmd = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = cmd.read_text(encoding="utf-8")

if "const changes =" not in text:
    insert_after = "const evidence = raceState.evidence.map((item) => item.title);\n"
    replacement = insert_after + """

const changes = raceState.timeline.map((item) => ({
  title: item.title,
  summary: item.summary,
}));

const raceContext = {
  updatedAt: "LIVE",
};
"""
    text = text.replace(insert_after, replacement)

cmd.write_text(text, encoding="utf-8")

# ------------------------------------------------------------------
# 2. adapters/index.ts
# remove wildcard exports to avoid SOURCE collisions
# ------------------------------------------------------------------

(Path("src/edgeiq-os/services/adapters/index.ts")).write_text("""
export type { IntelligenceAdapter } from "./AdapterTypes";

export { RaceShapeAdapter } from "./RaceShapeAdapter";
export { RunnerDNAAdapter } from "./RunnerDNAAdapter";
export { ExplainabilityAdapter } from "./ExplainabilityAdapter";
export { ConnectionAdapter } from "./ConnectionAdapter";
export { TrackAdapter } from "./TrackAdapter";
export { WeatherAdapter } from "./WeatherAdapter";
export { SectionalsAdapter } from "./SectionalsAdapter";
export { MarketAdapter } from "./MarketAdapter";

export { registerProductionAdapterSlots } from "./registerAdapters";
""".strip()+"\n", encoding="utf-8")

# ------------------------------------------------------------------
# 3. FeedLoader
# temporarily remove import.meta.glob
# ------------------------------------------------------------------

feed = Path("src/edgeiq-os/services/feed-loader/FeedLoader.ts")

feed.write_text("""
import type { FeedLoadResult } from "./FeedTypes";

export function loadBundledCsv(path: string): FeedLoadResult {
  return {
    path,
    loaded: false,
    rows: [],
    error:
      "Production feed loader temporarily disabled pending Vite asset integration.",
  };
}

export function clearFeedCache(): void {}
""".strip()+"\n", encoding="utf-8")

print("[EDGEIQ] Integration compile fixes applied")
