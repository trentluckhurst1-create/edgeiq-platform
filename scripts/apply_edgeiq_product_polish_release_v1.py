from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = "EDGEIQ_PRODUCT_POLISH_RELEASE_V1"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace(rel: str, old: str, new: str) -> None:
    text = read(rel)
    if old not in text:
        raise SystemExit(f"Missing expected snippet in {rel}: {old[:120]}")
    write(rel, text.replace(old, new))

presentation = r'''const PLACEHOLDER_VALUES = new Set([
  "",
  "-",
  "--",
  "UNAVAILABLE",
  "UNKNOWN",
  "NOT LOADED",
  "SOURCE GAP",
  "NULL",
  "UNDEFINED",
  "NAN",
  "NONE",
  "N/A",
  "NA",
]);

const TRACK_ALIASES: Array<[RegExp, string]> = [
  [/^SPORTSBET\s+BALLARAT\s+SYNTHETIC$/i, "Ball Syn"],
  [/^BALLARAT\s+SYNTHETIC$/i, "Ball Syn"],
  [/^SPORTSBET\s+BALLARAT$/i, "Ballarat"],
  [/^SPORTSBET\s+PAKENHAM\s+SYNTHETIC$/i, "Pak Syn"],
  [/^PAKENHAM\s+SYNTHETIC$/i, "Pak Syn"],
  [/^SPORTSBET\s+PAKENHAM$/i, "Pakenham"],
  [/^LADBROKES\s+GEELONG$/i, "Geelong"],
  [/^SPORTSBET\s+SANDOWN\s+HILLSIDE$/i, "Sandown Hillside"],
  [/^SPORTSBET\s+SANDOWN\s+LAKESIDE$/i, "Sandown Lakeside"],
];

export function cleanProductText(value: unknown, fallback = "-"): string {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (PLACEHOLDER_VALUES.has(text.toUpperCase())) return fallback;
  return text;
}

export function canonicalTrackDisplayName(value: unknown): string {
  let text = cleanProductText(value, "");
  if (!text) return "";
  text = text.replace(/\s+/g, " ").trim();
  for (const [pattern, replacement] of TRACK_ALIASES) {
    if (pattern.test(text)) return replacement;
  }
  return text
    .replace(/^SPORTSBET\s+/i, "")
    .replace(/^LADBROKES\s+/i, "")
    .replace(/^BET365\s+/i, "")
    .replace(/^TAB\s+/i, "")
    .trim();
}

function normaliseRecordTrackFields(record: Record<string, unknown> | undefined): Record<string, unknown> | undefined {
  if (!record) return record;
  const next: Record<string, unknown> = { ...record };
  for (const key of ["meeting", "meetingName", "track", "trackName", "venue", "venueName", "canonicalTrack", "displayTrack"]) {
    if (typeof next[key] === "string") next[key] = canonicalTrackDisplayName(next[key]);
  }
  return next;
}

export function normaliseCatalogTrackNames<T extends { meetings?: any[] }>(catalog: T): T {
  if (!catalog || !Array.isArray(catalog.meetings)) return catalog;
  return {
    ...catalog,
    meetings: catalog.meetings.map((meeting) => ({
      ...meeting,
      meeting: canonicalTrackDisplayName(meeting?.meeting),
      source: normaliseRecordTrackFields(meeting?.source),
      races: Array.isArray(meeting?.races)
        ? meeting.races.map((race: any) => ({
            ...race,
            source: normaliseRecordTrackFields(race?.source),
            runners: Array.isArray(race?.runners)
              ? race.runners.map((runner: any) => ({
                  ...runner,
                  source: normaliseRecordTrackFields(runner?.source),
                }))
              : race?.runners,
          }))
        : meeting?.races,
    })),
  };
}

export function marketDisplayStatus(status: unknown, hasMarket: boolean, isClosed = false): string {
  const text = cleanProductText(status, "");
  if (isClosed || /closed|scratched/i.test(text)) return "Market Closed";
  if (hasMarket || /available|live|snapshot/i.test(text)) return "Market Available";
  return "Awaiting Feed";
}
'''
write("src/edgeiq-os/design-system/presentation.ts", presentation)

# Wire catalogue-level sponsor stripping without changing keys.
replace(
    "src/edgeiq-os/race/services/threeDayCatalog.ts",
    'import { loadJsonFeed } from "../../services/feed-loader/ProductFeedCache";\n',
    'import { loadJsonFeed } from "../../services/feed-loader/ProductFeedCache";\nimport { normaliseCatalogTrackNames } from "../../design-system/presentation";\n',
)
replace(
    "src/edgeiq-os/race/services/threeDayCatalog.ts",
    '''  return loadJsonFeed<ThreeDayCatalog>(URL, {
    force,
    cacheKey: "three-day-product-catalog-v1",
    maxBytes: MAX_CATALOG_BYTES,
  });
''',
    '''  const catalog = await loadJsonFeed<ThreeDayCatalog>(URL, {
    force,
    cacheKey: "three-day-product-catalog-v1",
    maxBytes: MAX_CATALOG_BYTES,
  });
  return normaliseCatalogTrackNames(catalog);
''',
)

# Race workspace header track display.
replace(
    "src/edgeiq-os/race/components/RaceWorkspace.tsx",
    'import type { ThreeDayRace } from "../services/threeDayCatalog";\n',
    'import type { ThreeDayRace } from "../services/threeDayCatalog";\nimport { canonicalTrackDisplayName } from "../../design-system/presentation";\n',
)
replace(
    "src/edgeiq-os/race/components/RaceWorkspace.tsx",
    '  const meetingName = headerValue(official.meeting);\n',
    '  const meetingName = canonicalTrackDisplayName(headerValue(official.meeting));\n',
)

# Race intelligence copy and placeholders.
replace(
    "src/edgeiq-os/race/components/RaceIntelligenceWorkspace.tsx",
    'import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";\n',
    'import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";\nimport { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";\n',
)
replace(
    "src/edgeiq-os/race/components/RaceIntelligenceWorkspace.tsx",
    'function text(value: unknown, fallback = "Unavailable"): string {\n  const valueText = String(value ?? "").replace(/\\s+/g, " ").trim();\n  if (!valueText || valueText === "-" || ["null", "undefined", "none", "n/a", "na"].includes(valueText.toLowerCase())) return fallback;\n  return valueText;\n}\n',
    'function text(value: unknown, fallback = "-"): string {\n  return cleanProductText(value, fallback);\n}\n',
)
replace(
    "src/edgeiq-os/race/components/RaceIntelligenceWorkspace.tsx",
    '  const meeting = clean(official.meeting);\n',
    '  const meeting = canonicalTrackDisplayName(clean(official.meeting));\n',
)
# fix encoded chevrons and noisy placeholders.
text = read("src/edgeiq-os/race/components/RaceIntelligenceWorkspace.tsx")
text = text.replace(' <span>â€º</span> ', ' <span>/</span> ')
text = text.replace('Date unavailable', '-')
text = text.replace('Time unavailable', '-')
text = text.replace('Distance unavailable', '-')
text = text.replace('Surface unavailable', '-')
text = text.replace('Weather unavailable', '-')
text = text.replace('Prizemoney: {text(prizeMoney, "Unavailable")}', 'Prizemoney: {text(prizeMoney, "-")}')
write("src/edgeiq-os/race/components/RaceIntelligenceWorkspace.tsx", text)

# Meetings display: canonical track names and quieter table placeholders.
replace(
    "src/edgeiq-os/race/components/MeetingsWorkspace.tsx",
    'import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";\n',
    'import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";\nimport { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";\n',
)
replace(
    "src/edgeiq-os/race/components/MeetingsWorkspace.tsx",
    'function display(value: unknown, fallback = "Unavailable"): string {\n  const text = String(value ?? "").replace(/\\s+/g, " ").trim();\n  if (!text || text === "-" || ["null", "undefined", "none"].includes(text.toLowerCase())) return fallback;\n  return text;\n}\n',
    'function display(value: unknown, fallback = "-"): string {\n  return cleanProductText(value, fallback);\n}\n\nfunction displayTrack(value: unknown, fallback = "-"): string {\n  return canonicalTrackDisplayName(value) || fallback;\n}\n',
)
text = read("src/edgeiq-os/race/components/MeetingsWorkspace.tsx")
text = text.replace('{display(meeting.meeting)}', '{displayTrack(meeting.meeting)}')
text = text.replace('{display(meeting.state, "Not supplied")}', '{display(meeting.state)}')
text = text.replace('{display(meeting.rail, "Not supplied")}', '{display(meeting.rail)}')
text = text.replace('{display(meeting.track, "Not supplied")}', '{display(meeting.track)}')
text = text.replace('{display(meeting.weather, "Weather unavailable")}', '{display(meeting.weather)}')
write("src/edgeiq-os/race/components/MeetingsWorkspace.tsx", text)

# Meeting detail title displays canonical meeting.
replace(
    "src/edgeiq-os/race/components/MeetingWorkspace.tsx",
    'import { MeetingWeatherWorkspace } from "./MeetingWeatherWorkspace";\n',
    'import { MeetingWeatherWorkspace } from "./MeetingWeatherWorkspace";\nimport { canonicalTrackDisplayName } from "../../design-system/presentation";\n',
)
text = read("src/edgeiq-os/race/components/MeetingWorkspace.tsx")
text = text.replace('{model.meeting}', '{canonicalTrackDisplayName(model.meeting)}')
text = text.replace('{meeting.meeting}', '{canonicalTrackDisplayName(meeting.meeting)}')
write("src/edgeiq-os/race/components/MeetingWorkspace.tsx", text)

# Form guide placeholder and canonical tracks in historical runs.
replace(
    "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx",
    'import { buildRunnerProfileDossier } from "../services/formGuideWorkspaceViewModel";\n',
    'import { buildRunnerProfileDossier } from "../services/formGuideWorkspaceViewModel";\nimport { canonicalTrackDisplayName } from "../../design-system/presentation";\n',
)
text = read("src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx")
text = text.replace('const DASH = "â€”";', 'const DASH = "-";')
text = text.replace('const DASH = "—";', 'const DASH = "-";')
text = text.replace('<td>{cleanDisplay(run.track)}</td>', '<td>{cleanDisplay(canonicalTrackDisplayName(run.track))}</td>')
text = text.replace('No governed match insight is available for this runner.', 'Match profile requires governed evidence for this runner.')
text = text.replace('No governed recent-form rows available.', 'No governed recent-form rows are published for this runner.')
write("src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx", text)

# Market language and statuses.
replace(
    "src/edgeiq-os/race/components/MarketWorkspace.tsx",
    'import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";\n',
    'import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";\nimport { marketDisplayStatus } from "../../design-system/presentation";\n',
)
text = read("src/edgeiq-os/race/components/MarketWorkspace.tsx")
text = text.replace('return "FLUCTUATION UNAVAILABLE";', 'return "Movement not published";')
text = text.replace('if (row.marketIsLive) return "LIVE MARKET";\n  if (row.marketAvailabilityStatus === "MARKET_SNAPSHOT") return "EDGE VS SNAPSHOT";\n  if (row.marketFreshnessStatus === "MARKET_STALE") return "STALE MARKET";\n  return "MARKET UNAVAILABLE";', 'if (row.marketIsLive) return "Market Available";\n  if (row.marketAvailabilityStatus === "MARKET_SNAPSHOT") return "Market Available";\n  if (row.marketFreshnessStatus === "MARKET_STALE") return "Market Closed";\n  return "Awaiting Feed";')
text = text.replace('return value(row.status) || (row.market || row.edgeiq_price ? "Available" : "Pending Market");', 'return marketDisplayStatus(row.status, Boolean(row.market || row.edgeiq_price), row.rowStatus === "scratched");')
text = text.replace('<td>{value(row.epi) || "Unavailable"}</td>', '<td>{value(row.epi) || "-"}</td>')
text = text.replace('<td><b className={edgeClass(row)}>{value(row.edge) || "Pending"}</b></td>', '<td><b className={edgeClass(row)}>{value(row.edge) || "-"}</b></td>')
text = text.replace('Market prices are disclosed as live only when a timestamp-safe live observation exists. Snapshot prices are labelled and fluctuation is unavailable unless valid movement evidence exists.', 'Market prices use the governed observation feed. Movement appears only where timestamp-safe fluctuation evidence is published.')
text = text.replace('<div><dt>Market State</dt><dd>{viewModel.rows.some((row) => row.marketAvailabilityStatus === "MARKET_SNAPSHOT") ? "Snapshot" : "Unavailable"}</dd></div>', '<div><dt>Market State</dt><dd>{viewModel.rows.some((row) => row.market || row.edgeiq_price) ? "Market Available" : "Awaiting Feed"}</dd></div>')
text = text.replace('Governed market rows are not available for this race.', 'Governed market rows are not published for this race.')
write("src/edgeiq-os/race/components/MarketWorkspace.tsx", text)

# Map track display.
replace(
    "src/edgeiq-os/race/components/MapWorkspace.tsx",
    'import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";\n',
    'import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";\nimport { canonicalTrackDisplayName } from "../../design-system/presentation";\n',
)
replace(
    "src/edgeiq-os/race/components/MapWorkspace.tsx",
    '''function raceTrackName(raceBook: RaceBook): string {
  const official = (raceBook.official ?? {}) as Record<string, unknown>;
  const source = (raceBook.source ?? {}) as Record<string, unknown>;
  return firstText(
    official.track,
    official.meeting,
    source.track,
    source.meeting,
    source.meetingName,
  );
}
''',
    '''function raceTrackName(raceBook: RaceBook): string {
  const official = (raceBook.official ?? {}) as Record<string, unknown>;
  const source = (raceBook.source ?? {}) as Record<string, unknown>;
  return canonicalTrackDisplayName(firstText(
    official.track,
    official.meeting,
    source.track,
    source.meeting,
    source.meetingName,
  ));
}
'''
)

# Field table placeholders and product copy.
text = read("src/edgeiq-os/race/components/FieldWorkspace.tsx")
text = text.replace('Official runners with governed EDGEiQ fields where available.', 'Official runners with governed EDGEiQ fields.')
text = text.replace('runner.barrier || "-"', 'runner.barrier || "-"')
text = text.replace('Governed recent-start rows are not available for this runner.', 'Governed recent-start rows are not published for this runner.')
write("src/edgeiq-os/race/components/FieldWorkspace.tsx", text)

# Append shared product design system layer.
css_path = "src/edgeiq-os/styles/edgeiqOsV2.css"
css = read(css_path)
polish = r'''

/* EDGEIQ PRODUCT POLISH RELEASE V1
   Shared professional operating-system standards. Presentation only; no model maths. */
:root {
  --eiq-product-font: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --eiq-product-bg: #ffffff;
  --eiq-product-panel: #ffffff;
  --eiq-product-panel-soft: #f8fafc;
  --eiq-product-border: #dfe5ee;
  --eiq-product-border-soft: #edf1f6;
  --eiq-product-text: #172033;
  --eiq-product-muted: #5f6b7a;
  --eiq-product-faint: #7a8595;
  --eiq-product-blue: #2456b8;
  --eiq-product-green: #1f8f5f;
  --eiq-product-red: #b42318;
  --eiq-product-radius: 10px;
  --eiq-product-card-padding: 16px;
  --eiq-product-row: 38px;
  --eiq-product-head: 40px;
}

.edgeiq-os,
.edgeiq-os * {
  font-family: var(--eiq-product-font) !important;
  letter-spacing: 0 !important;
  text-shadow: none !important;
}

.edgeiq-os * {
  background-image: none !important;
}

.edgeiq-os h1,
.edgeiq-os .eiq-approved-racefile-header__title h1,
.edgeiq-os .eiq-approved-race__context h1,
.edgeiq-os .eiq-meetings-approved__header h1 {
  font-size: 18px !important;
  line-height: 1.25 !important;
  font-weight: 700 !important;
  color: var(--eiq-product-text) !important;
  margin: 0 !important;
}

.edgeiq-os h2,
.edgeiq-os h3,
.edgeiq-os [class*="__title"] strong,
.edgeiq-os [class*="panel__title"] span,
.edgeiq-os section > header strong {
  font-size: 15px !important;
  line-height: 1.3 !important;
  font-weight: 700 !important;
  color: var(--eiq-product-text) !important;
  text-transform: uppercase;
}

.edgeiq-os p,
.edgeiq-os span,
.edgeiq-os small,
.edgeiq-os dt,
.edgeiq-os dd,
.edgeiq-os button,
.edgeiq-os input,
.edgeiq-os td {
  font-size: 13px !important;
  font-weight: 500 !important;
}

.edgeiq-os small,
.edgeiq-os dt,
.edgeiq-os [class*="meta"] span,
.edgeiq-os [class*="crumb"],
.edgeiq-os [class*="__title"] p {
  font-size: 12px !important;
  color: var(--eiq-product-muted) !important;
}

.edgeiq-os table {
  width: 100%;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed;
  background: var(--eiq-product-panel) !important;
  border: 1px solid var(--eiq-product-border) !important;
  border-radius: var(--eiq-product-radius) !important;
  overflow: hidden;
}

.edgeiq-os thead th {
  height: var(--eiq-product-head) !important;
  padding: 0 10px !important;
  text-align: center !important;
  vertical-align: middle !important;
  color: var(--eiq-product-muted) !important;
  background: var(--eiq-product-panel-soft) !important;
  border-bottom: 1px solid var(--eiq-product-border) !important;
  font-size: 13px !important;
  line-height: 1.15 !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  white-space: normal !important;
}

.edgeiq-os tbody td {
  height: var(--eiq-product-row) !important;
  padding: 0 10px !important;
  text-align: center !important;
  vertical-align: middle !important;
  border-bottom: 1px solid var(--eiq-product-border-soft) !important;
  color: var(--eiq-product-text) !important;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edgeiq-os tbody tr:last-child td {
  border-bottom: 0 !important;
}

.edgeiq-os th.is-left,
.edgeiq-os td.is-left,
.edgeiq-os .eiq-field-table-v1 td:nth-child(3),
.edgeiq-os .eiq-field-table-v1 td:nth-child(6),
.edgeiq-os .eiq-field-table-v1 td:nth-child(7),
.edgeiq-os .eiq-form-summary-table td:nth-child(4),
.edgeiq-os .eiq-form-summary-table td:nth-child(5),
.edgeiq-os .eiq-form-summary-table td:nth-child(6),
.edgeiq-os .eiq-market-v1-table td:nth-child(2),
.edgeiq-os .eiq-meeting-v1-table td:nth-child(3),
.edgeiq-os .eiq-approved-table td:nth-child(3) {
  text-align: left !important;
}

.edgeiq-os .eiq-field-table-v1 td:nth-child(3) strong,
.edgeiq-os .eiq-form-summary-table td:nth-child(4) strong,
.edgeiq-os .eiq-market-v1-table td:nth-child(2) strong {
  font-weight: 700 !important;
}

.edgeiq-os .eiq-workspace-panel,
.edgeiq-os .eiq-market-v1-panel,
.edgeiq-os .eiq-epi-v1-panel,
.edgeiq-os .eiq-meeting-v1-panel,
.edgeiq-os .eiq-approved-race__panel,
.edgeiq-os .eiq-meetings-approved__table-panel,
.edgeiq-os .eiq-meetings-approved__timeline,
.edgeiq-os .eiq-form-runner-profile,
.edgeiq-os .eiq-form-profile-card,
.edgeiq-os .eiq-map-panel,
.edgeiq-os .eiq-barrier-map-panel,
.edgeiq-os .edge-card,
.edgeiq-os .eiq-workspace-card {
  background: var(--eiq-product-panel) !important;
  border: 1px solid var(--eiq-product-border) !important;
  border-radius: var(--eiq-product-radius) !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
  padding: var(--eiq-product-card-padding) !important;
}

.edgeiq-os .eiq-context-tabs,
.edgeiq-os .eiq-approved-race__tabs,
.edgeiq-os nav[aria-label*="navigation"] {
  min-height: 40px !important;
  border: 1px solid var(--eiq-product-border) !important;
  background: var(--eiq-product-panel) !important;
  border-radius: var(--eiq-product-radius) !important;
  padding: 4px !important;
  gap: 4px !important;
}

.edgeiq-os .eiq-context-tabs button,
.edgeiq-os .eiq-approved-button,
.edgeiq-os .eiq-meetings-approved__select,
.edgeiq-os .eiq-field-runner-button,
.edgeiq-os button {
  border-radius: 8px !important;
  font-size: 12px !important;
  font-weight: 600 !important;
}

.edgeiq-os .is-positive,
.edgeiq-os [data-direction="up"] {
  color: var(--eiq-product-green) !important;
}

.edgeiq-os .is-negative,
.edgeiq-os [data-direction="down"] {
  color: var(--eiq-product-red) !important;
}

.edgeiq-os .is-neutral,
.edgeiq-os .is-current,
.edgeiq-os .is-selected,
.edgeiq-os .is-active {
  color: var(--eiq-product-blue) !important;
}

.edgeiq-os .is-soft,
.edgeiq-os .is-heavy,
.edgeiq-os .is-good,
.edgeiq-os .is-firm {
  color: var(--eiq-product-text) !important;
  background: transparent !important;
}

.edgeiq-os .eiq-market-v1-hero,
.edgeiq-os .eiq-race-form-guide__hero,
.edgeiq-os .eiq-approved-race__context,
.edgeiq-os .eiq-meetings-approved__header,
.edgeiq-os .eiq-map-workspace__header,
.edgeiq-os .eiq-epi-v1-hero {
  background: var(--eiq-product-panel) !important;
  border: 1px solid var(--eiq-product-border) !important;
  border-radius: var(--eiq-product-radius) !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
}

.edgeiq-os .eiq-form-tooltip-trigger,
.edgeiq-os .eiq-form-summary-table th button {
  width: 100%;
  text-align: center !important;
  justify-content: center;
}

.edgeiq-os .eiq-form-last5-strip {
  justify-content: center !important;
}

.edgeiq-os .eiq-map-lane,
.edgeiq-os .eiq-barrier-map-lane {
  background: #eef4ff !important;
  border-color: var(--eiq-product-border) !important;
}

.edgeiq-os .eiq-map-runner-chip,
.edgeiq-os .eiq-barrier-map-runner {
  background: #ffffff !important;
  border: 1px solid var(--eiq-product-blue) !important;
  color: var(--eiq-product-text) !important;
}

.edgeiq-os .eiq-field-expanded-row td {
  height: auto !important;
  padding: 12px !important;
  text-align: left !important;
}
'''
if "EDGEIQ PRODUCT POLISH RELEASE V1" not in css:
    css += polish
write(css_path, css)

print("EDGEIQ_PRODUCT_POLISH_RELEASE_V1_APPLIED")
