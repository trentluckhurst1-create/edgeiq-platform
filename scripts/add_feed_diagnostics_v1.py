from pathlib import Path

diag = Path("src/edgeiq-os/services/feed-diagnostics")
diag.mkdir(parents=True, exist_ok=True)

(diag / "FeedDiagnosticsService.ts").write_text(r'''
import { pick } from "../feed-loader";
import type { FeedRow } from "../feed-loader";
import type { ActiveRaceContext } from "../feed-context";

function normalise(value: string): string {
  return value.trim().toUpperCase();
}

export function describeFeedMatch(
  rows: FeedRow[],
  context: ActiveRaceContext,
  label: string,
): string {
  if (!rows.length) {
    return `${label}: feed loaded but contains no rows for active race ${context.track} R${context.raceNo}.`;
  }

  const sample = rows[0];
  const track = normalise(pick(sample, ["track", "normalised_track"], "UNKNOWN"));
  const raceNo = pick(sample, ["race_no"], "UNKNOWN");
  const raceDate = pick(sample, ["race_date"], "");

  if (track === context.track && raceNo === context.raceNo) {
    return `${label}: active race match ${context.track} R${context.raceNo}${raceDate ? ` (${raceDate})` : ""}; ${rows.length} row(s) available.`;
  }

  return `${label}: no active race match for ${context.track} R${context.raceNo}. Latest available sample is ${track} R${raceNo}${raceDate ? ` (${raceDate})` : ""}.`;
}

export function describeActiveRace(context: ActiveRaceContext): string {
  return `${context.track} R${context.raceNo}${context.raceDate ? ` (${context.raceDate})` : ""}`;
}
''', encoding="utf-8")

(diag / "index.ts").write_text(r'''
export * from "./FeedDiagnosticsService";
''', encoding="utf-8")

for path in Path("src/edgeiq-os/services/adapters").glob("*Adapter.ts"):
    text = path.read_text(encoding="utf-8")
    if "describeFeedMatch" not in text and "buildIntelligenceSnapshot" in text:
        text = text.replace(
            'import { buildIntelligenceSnapshot } from "../intelligence-snapshot";',
            'import { buildIntelligenceSnapshot } from "../intelligence-snapshot";\nimport { describeFeedMatch } from "../feed-diagnostics";'
        )
    text = text.replace(
        'freshness: "No active-race match"',
        'freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics")'
    )
    text = text.replace(
        '`Snapshot active race ${snapshot.context.track} R${snapshot.context.raceNo}; no match`',
        'describeFeedMatch(rows, snapshot.context, "Feed diagnostics")'
    )
    text = text.replace(
        '`Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${rows.length} runners`',
        'describeFeedMatch(rows, snapshot.context, "Feed diagnostics")'
    )
    text = text.replace(
        '`Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${rows.length} market row(s)`',
        'describeFeedMatch(rows, snapshot.context, "Feed diagnostics")'
    )
    path.write_text(text, encoding="utf-8")

print("[EDGEIQ] Feed diagnostics service created and wired into adapters")
