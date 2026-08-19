from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMPARE_SERVICE = r'''import type {
  HistoricalPerformanceIntelligenceRow,
  HorseIntelligenceIndexRow,
  PerformanceIntelligenceFeed,
  RaceIntelligenceIndexRow,
} from "../services/performance-intelligence";

export type CompareEntityMode = "HORSE" | "RACE";

export type CompareEntityOption = {
  id: string;
  label: string;
  meta: string;
};

export type CompareUnavailableMode = {
  label: string;
  reason: string;
};

export type CompareMetricRow = {
  label: string;
  left: string;
  right: string;
  scope: string;
};

export type ComparePanel = {
  title: string;
  subtitle: string;
  rows: CompareMetricRow[];
};

export type CompareHistoricalPairRow = {
  id: string;
  side: "Left" | "Right";
  date: string;
  race: string;
  distance: string;
  className: string;
  condition: string;
  finish: string;
  margin: string;
  sp: string;
  benchmark: string;
};

export type CompareViewModel = {
  mode: CompareEntityMode;
  options: CompareEntityOption[];
  leftPanel: ComparePanel | null;
  rightPanel: ComparePanel | null;
  metricRows: CompareMetricRow[];
  historicalRows: CompareHistoricalPairRow[];
  unavailableModes: CompareUnavailableMode[];
  feedGenerated: string;
  limitationText: string;
};

const UNAVAILABLE = "Unavailable";

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function value(value: unknown): string {
  return clean(value) || UNAVAILABLE;
}

function titleCase(value: unknown): string {
  const text = clean(value);
  if (!text) return UNAVAILABLE;
  return text
    .toLowerCase()
    .split(/[\s_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function numberKey(value: unknown): number {
  const parsed = Number(clean(value).replace(/[^\d.]/g, ""));
  return Number.isFinite(parsed) ? parsed : 9999;
}

function normaliseKey(value: unknown): string {
  return clean(value).toUpperCase();
}

function horseId(row: HorseIntelligenceIndexRow): string {
  return ["HORSE", row.race_context_key, row.runner_number, row.horse_code || row.horse_name].map(clean).join("|");
}

function raceId(row: RaceIntelligenceIndexRow): string {
  return ["RACE", row.race_context_key].map(clean).join("|");
}

function raceLabel(row: RaceIntelligenceIndexRow): string {
  const track = value(row.track);
  const raceNo = clean(row.race_number).replace(/^R/i, "");
  return `${track} R${raceNo || "?"}`;
}

function raceMeta(row: RaceIntelligenceIndexRow): string {
  return [row.race_date, row.distance_metres ? `${row.distance_metres}m` : "", row.race_class, row.track_condition]
    .map(clean)
    .filter(Boolean)
    .join(" | ");
}

function horseMeta(row: HorseIntelligenceIndexRow): string {
  const runner = clean(row.runner_number) ? `No ${clean(row.runner_number)}` : "";
  return [runner, row.date_range, `${value(row.performance_count)} starts`].filter(Boolean).join(" | ");
}

function scopedHorses(feed: PerformanceIntelligenceFeed, raceKey?: string | null): HorseIntelligenceIndexRow[] {
  const key = normaliseKey(raceKey);
  const rows = key
    ? feed.horse_intelligence_index.filter((row) => normaliseKey(row.race_context_key) === key)
    : feed.horse_intelligence_index;

  return [...rows]
    .filter((row) => clean(row.horse_name))
    .sort((a, b) => {
      const raceOrder = normaliseKey(a.race_context_key).localeCompare(normaliseKey(b.race_context_key));
      if (raceOrder !== 0) return raceOrder;
      return numberKey(a.runner_number) - numberKey(b.runner_number);
    });
}

function raceRows(feed: PerformanceIntelligenceFeed): RaceIntelligenceIndexRow[] {
  return [...feed.race_intelligence_index]
    .filter((row) => clean(row.race_context_key))
    .sort((a, b) => {
      const dateOrder = clean(a.race_date).localeCompare(clean(b.race_date));
      if (dateOrder !== 0) return dateOrder;
      const trackOrder = clean(a.track).localeCompare(clean(b.track));
      if (trackOrder !== 0) return trackOrder;
      return numberKey(a.race_number) - numberKey(b.race_number);
    });
}

export function getCompareOptions(
  feed: PerformanceIntelligenceFeed | null,
  mode: CompareEntityMode,
  raceKey?: string | null,
): CompareEntityOption[] {
  if (!feed) return [];
  if (mode === "RACE") {
    return raceRows(feed).map((row) => ({ id: raceId(row), label: raceLabel(row), meta: raceMeta(row) }));
  }

  return scopedHorses(feed, raceKey).map((row) => ({
    id: horseId(row),
    label: value(row.horse_name),
    meta: horseMeta(row),
  }));
}

function findHorse(feed: PerformanceIntelligenceFeed, id: string): HorseIntelligenceIndexRow | null {
  return scopedHorses(feed).find((row) => horseId(row) === id) ?? null;
}

function findRace(feed: PerformanceIntelligenceFeed, id: string): RaceIntelligenceIndexRow | null {
  return raceRows(feed).find((row) => raceId(row) === id) ?? null;
}

function horseMetricRows(left: HorseIntelligenceIndexRow | null, right: HorseIntelligenceIndexRow | null): CompareMetricRow[] {
  const pairs: Array<[string, keyof HorseIntelligenceIndexRow, string]> = [
    ["Profile State", "profile_quality_state", "Horse profile"],
    ["Identity State", "identity_quality_state", "Horse profile"],
    ["Performance Count", "performance_count", "Eligible historical runs"],
    ["Eligible Performances", "eligible_performance_count", "Eligible historical runs"],
    ["Date Range", "date_range", "Historical coverage"],
    ["Track Profile", "track_profile", "Comparable profile"],
    ["Distance Profile", "distance_profile", "Comparable profile"],
    ["Condition Profile", "going_profile", "Comparable profile"],
    ["Class Profile", "class_profile", "Comparable profile"],
    ["Pressure Profile", "pressure_profile", "Race shape"],
    ["Late Speed Profile", "late_speed_profile", "Race shape"],
    ["Consistency Profile", "consistency_profile", "Performance pattern"],
  ];

  return pairs.map(([label, key, scope]) => ({
    label,
    left: value(left?.[key]),
    right: value(right?.[key]),
    scope,
  }));
}

function raceMetricRows(left: RaceIntelligenceIndexRow | null, right: RaceIntelligenceIndexRow | null): CompareMetricRow[] {
  const pairs: Array<[string, keyof RaceIntelligenceIndexRow, string]> = [
    ["Meeting", "meeting", "Race identity"],
    ["Race Date", "race_date", "Race identity"],
    ["Race Name", "race_name", "Race identity"],
    ["Distance", "distance_metres", "Race conditions"],
    ["Class", "race_class", "Race conditions"],
    ["Track Condition", "track_condition", "Race conditions"],
    ["Rail", "rail_position", "Race conditions"],
    ["Runner Count", "runner_count", "Field composition"],
    ["Race Quality", "race_quality_state", "Governed assessment"],
    ["Benchmark Level", "selected_benchmark_level", "Benchmark selection"],
    ["Benchmark Sample", "selected_benchmark_sample_size", "Benchmark selection"],
    ["Fingerprint", "fingerprint_pattern", "Race pattern"],
    ["Fingerprint State", "fingerprint_quality_state", "Race pattern"],
  ];

  return pairs.map(([label, key, scope]) => ({
    label,
    left: value(left?.[key]),
    right: value(right?.[key]),
    scope,
  }));
}

function horsePanel(row: HorseIntelligenceIndexRow | null, side: string): ComparePanel | null {
  if (!row) return null;
  return {
    title: value(row.horse_name),
    subtitle: horseMeta(row),
    rows: [
      { label: "Profile State", left: titleCase(row.profile_quality_state), right: "", scope: side },
      { label: "Runs", left: value(row.performance_count), right: "", scope: side },
      { label: "Eligible Runs", left: value(row.eligible_performance_count), right: "", scope: side },
      { label: "Date Range", left: value(row.date_range), right: "", scope: side },
    ],
  };
}

function racePanel(row: RaceIntelligenceIndexRow | null, side: string): ComparePanel | null {
  if (!row) return null;
  return {
    title: raceLabel(row),
    subtitle: raceMeta(row),
    rows: [
      { label: "Race Quality", left: titleCase(row.race_quality_state), right: "", scope: side },
      { label: "Runners", left: value(row.runner_count), right: "", scope: side },
      { label: "Benchmark", left: value(row.selected_benchmark_level), right: "", scope: side },
      { label: "Pattern", left: value(row.fingerprint_pattern), right: "", scope: side },
    ],
  };
}

function historicalForHorse(feed: PerformanceIntelligenceFeed, horse: HorseIntelligenceIndexRow | null): HistoricalPerformanceIntelligenceRow[] {
  if (!horse) return [];
  const raceKey = normaliseKey(horse.race_context_key);
  const runner = clean(horse.runner_number);
  const horseCode = normaliseKey(horse.horse_code);
  const horseName = normaliseKey(horse.horse_name);
  return feed.historical_performance_intelligence_index
    .filter((row) => {
      if (normaliseKey(row.current_race_context_key) !== raceKey) return false;
      if (runner && clean(row.runner_number) === runner) return true;
      if (horseCode && normaliseKey(row.horse_code) === horseCode) return true;
      return Boolean(horseName && normaliseKey(row.horse) === horseName);
    })
    .sort((a, b) => clean(b.race_date).localeCompare(clean(a.race_date)))
    .slice(0, 5);
}

function toHistoricalPairRows(side: "Left" | "Right", rows: HistoricalPerformanceIntelligenceRow[]): CompareHistoricalPairRow[] {
  return rows.map((row) => ({
    id: `${side}-${row.performance_fact_id || row.legacy_performance_fact_id || row.race_date}-${row.race_number}`,
    side,
    date: value(row.race_date),
    race: [row.track, row.race_number].map(clean).filter(Boolean).join(" R") || UNAVAILABLE,
    distance: clean(row.distance_metres) ? `${clean(row.distance_metres)}m` : UNAVAILABLE,
    className: value(row.race_class),
    condition: value(row.track_condition),
    finish: value(row.finish_position),
    margin: value(row.margin_raw || row.margin_lengths_raw),
    sp: value(row.starting_price),
    benchmark: value(row.benchmark_level),
  }));
}

export function defaultCompareSelection(options: CompareEntityOption[]): { leftId: string; rightId: string } {
  return {
    leftId: options[0]?.id ?? "",
    rightId: options[1]?.id ?? options[0]?.id ?? "",
  };
}

export function buildCompareViewModel(
  feed: PerformanceIntelligenceFeed | null,
  mode: CompareEntityMode,
  leftId: string,
  rightId: string,
  raceKey?: string | null,
): CompareViewModel {
  const options = getCompareOptions(feed, mode, raceKey);
  const unavailableModes = [
    { label: "Jockey", reason: "Governed side-by-side jockey comparison is not available in the current product feed." },
    { label: "Trainer", reason: "Governed side-by-side trainer comparison is not available in the current product feed." },
    { label: "Track", reason: "Governed side-by-side track comparison is not available in the current product feed." },
  ];

  if (!feed || options.length === 0) {
    return {
      mode,
      options,
      leftPanel: null,
      rightPanel: null,
      metricRows: [],
      historicalRows: [],
      unavailableModes,
      feedGenerated: "",
      limitationText: "Governed comparison data is not available for this context.",
    };
  }

  const selection = defaultCompareSelection(options);
  const safeLeftId = options.some((option) => option.id === leftId) ? leftId : selection.leftId;
  const safeRightId = options.some((option) => option.id === rightId) ? rightId : selection.rightId;

  if (mode === "RACE") {
    const leftRace = findRace(feed, safeLeftId);
    const rightRace = findRace(feed, safeRightId);
    return {
      mode,
      options,
      leftPanel: racePanel(leftRace, "Left"),
      rightPanel: racePanel(rightRace, "Right"),
      metricRows: raceMetricRows(leftRace, rightRace),
      historicalRows: [],
      unavailableModes,
      feedGenerated: clean(feed.manifest.generated_timestamp),
      limitationText: "Race comparison is limited to fields governed by the certified performance intelligence feed.",
    };
  }

  const leftHorse = findHorse(feed, safeLeftId);
  const rightHorse = findHorse(feed, safeRightId);
  return {
    mode,
    options,
    leftPanel: horsePanel(leftHorse, "Left"),
    rightPanel: horsePanel(rightHorse, "Right"),
    metricRows: horseMetricRows(leftHorse, rightHorse),
    historicalRows: [
      ...toHistoricalPairRows("Left", historicalForHorse(feed, leftHorse)),
      ...toHistoricalPairRows("Right", historicalForHorse(feed, rightHorse)),
    ],
    unavailableModes,
    feedGenerated: clean(feed.manifest.generated_timestamp),
    limitationText: "Only common governed fields are compared. Different sample sizes and date ranges remain visible.",
  };
}
'''

COMPARE_WORKSPACE = r'''import { useEffect, useMemo, useState } from "react";
import {
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceFeed,
} from "../services/performance-intelligence";
import {
  buildCompareViewModel,
  defaultCompareSelection,
  getCompareOptions,
  type CompareEntityMode,
  type CompareMetricRow,
  type ComparePanel,
} from "./compareWorkspaceData";

type CompareWorkspaceProps = {
  raceKey?: string | null;
  runner?: any;
};

const MODES: CompareEntityMode[] = ["HORSE", "RACE"];

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  return text || "Unavailable";
}

function runnerIdentity(runner: any): string {
  return String(runner?.horse ?? runner?.runnerName ?? runner?.name ?? "").trim();
}

function Panel({ label, panel }: { label: string; panel: ComparePanel | null }) {
  if (!panel) {
    return (
      <article className="eiq-compare-final-card">
        <span>{label}</span>
        <strong>Unavailable</strong>
        <p>Choose a governed entity to compare.</p>
      </article>
    );
  }

  return (
    <article className="eiq-compare-final-card">
      <span>{label}</span>
      <strong>{panel.title}</strong>
      <p>{panel.subtitle}</p>
      <dl>
        {panel.rows.map((row) => (
          <div key={`${label}-${row.label}`}>
            <dt>{row.label}</dt>
            <dd>{row.left}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function MetricRow({ row }: { row: CompareMetricRow }) {
  return (
    <tr>
      <th scope="row">{row.label}</th>
      <td>{row.left}</td>
      <td>{row.right}</td>
      <td>{row.scope}</td>
    </tr>
  );
}

export function CompareWorkspace({ raceKey, runner }: CompareWorkspaceProps) {
  const [feed, setFeed] = useState<PerformanceIntelligenceFeed | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [mode, setMode] = useState<CompareEntityMode>("HORSE");
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");

  useEffect(() => {
    let cancelled = false;
    loadPerformanceIntelligenceFeed()
      .then((nextFeed) => {
        if (cancelled) return;
        setFeed(nextFeed);
        setLoadState("ready");
        const options = getCompareOptions(nextFeed, "HORSE", raceKey);
        const selection = defaultCompareSelection(options);
        const runnerName = runnerIdentity(runner).toUpperCase();
        const runnerOption = runnerName
          ? options.find((option) => option.label.toUpperCase() === runnerName)
          : null;
        setLeftId(runnerOption?.id ?? selection.leftId);
        setRightId(selection.rightId === runnerOption?.id ? (options[1]?.id ?? selection.rightId) : selection.rightId);
      })
      .catch((error) => {
        console.warn("EDGEiQ compare feed unavailable", error);
        if (!cancelled) {
          setFeed(null);
          setLoadState("unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey, runner]);

  const options = useMemo(() => getCompareOptions(feed, mode, raceKey), [feed, mode, raceKey]);
  const viewModel = useMemo(
    () => buildCompareViewModel(feed, mode, leftId, rightId, raceKey),
    [feed, mode, leftId, rightId, raceKey],
  );

  useEffect(() => {
    if (!options.length) {
      setLeftId("");
      setRightId("");
      return;
    }
    const selection = defaultCompareSelection(options);
    if (!options.some((option) => option.id === leftId)) setLeftId(selection.leftId);
    if (!options.some((option) => option.id === rightId)) setRightId(selection.rightId);
  }, [options, leftId, rightId]);

  return (
    <section className="eiq-compare-final">
      <header className="eiq-compare-final__header">
        <div>
          <span>COMPARE</span>
          <strong>Side-by-side governed comparison</strong>
          <p>
            Compare horses or races using common certified performance fields. Values that are not present in the governed feed remain unavailable.
          </p>
        </div>
        <aside>
          <span>Feed</span>
          <strong>{loadState === "ready" ? "Loaded" : loadState === "loading" ? "Loading" : "Unavailable"}</strong>
          <small>{clean(viewModel.feedGenerated)}</small>
        </aside>
      </header>

      <div className="eiq-compare-final__controls">
        <label>
          <span>Entity</span>
          <select
            value={mode}
            onChange={(event) => {
              const nextMode = event.target.value as CompareEntityMode;
              setMode(nextMode);
              const selection = defaultCompareSelection(getCompareOptions(feed, nextMode, raceKey));
              setLeftId(selection.leftId);
              setRightId(selection.rightId);
            }}
          >
            {MODES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Left</span>
          <select value={leftId} onChange={(event) => setLeftId(event.target.value)} disabled={!options.length}>
            {options.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Right</span>
          <select value={rightId} onChange={(event) => setRightId(event.target.value)} disabled={!options.length}>
            {options.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </label>
        <div className="eiq-compare-final__scope">
          <span>Scope</span>
          <strong>{mode === "HORSE" ? "Current race runners" : "Certified races"}</strong>
        </div>
      </div>

      <div className="eiq-compare-final__panels">
        <Panel label="Left" panel={viewModel.leftPanel} />
        <Panel label="Right" panel={viewModel.rightPanel} />
        <aside className="eiq-compare-final-card eiq-compare-final__boundary">
          <span>Data Boundary</span>
          <strong>Comparable fields only</strong>
          <p>{viewModel.limitationText}</p>
          <ul>
            {viewModel.unavailableModes.map((item) => (
              <li key={item.label}><b>{item.label}</b><em>{item.reason}</em></li>
            ))}
          </ul>
        </aside>
      </div>

      <section className="eiq-compare-final-table">
        <header>
          <span>Common Metrics</span>
          <strong>{mode === "HORSE" ? "Profile alignment" : "Race context alignment"}</strong>
        </header>
        <div>
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Left</th>
                <th>Right</th>
                <th>Scope</th>
              </tr>
            </thead>
            <tbody>
              {viewModel.metricRows.map((row) => <MetricRow key={row.label} row={row} />)}
            </tbody>
          </table>
        </div>
      </section>

      <section className="eiq-compare-final-table">
        <header>
          <span>Historical Context</span>
          <strong>{mode === "HORSE" ? "Recent governed runs" : "Not applicable for race comparison"}</strong>
        </header>
        {mode === "HORSE" && viewModel.historicalRows.length ? (
          <div>
            <table>
              <thead>
                <tr>
                  <th>Side</th>
                  <th>Date</th>
                  <th>Race</th>
                  <th>Dist</th>
                  <th>Class</th>
                  <th>Cond</th>
                  <th>Finish</th>
                  <th>Margin</th>
                  <th>SP</th>
                  <th>Benchmark</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.historicalRows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.side}</td>
                    <td>{row.date}</td>
                    <td>{row.race}</td>
                    <td>{row.distance}</td>
                    <td>{row.className}</td>
                    <td>{row.condition}</td>
                    <td>{row.finish}</td>
                    <td>{row.margin}</td>
                    <td>{row.sp}</td>
                    <td>{row.benchmark}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="eiq-compare-final__empty">
            {mode === "HORSE"
              ? "Historical governed rows are not available for this selection."
              : "Race comparison uses race-level governed fields only."}
          </p>
        )}
      </section>
    </section>
  );
}
'''

CSS_APPEND = r'''

/* EDGEIQ COMPARE FINAL SPEC V1 */
.eiq-compare-final {
  display: grid;
  gap: 16px;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-compare-final__header,
.eiq-compare-final-card,
.eiq-compare-final-table,
.eiq-compare-final__controls {
  background: var(--edgeiq-surface, #ffffff);
  border: 1px solid var(--edgeiq-border, #d9e2ec);
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(15, 31, 48, 0.06);
}

.eiq-compare-final__header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px;
}

.eiq-compare-final__header span,
.eiq-compare-final-card > span,
.eiq-compare-final-table > header span,
.eiq-compare-final__controls label span,
.eiq-compare-final__scope span {
  display: block;
  color: var(--edgeiq-primary, #1167b1);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-compare-final__header strong {
  display: block;
  margin-top: 6px;
  font-size: 24px;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-compare-final__header p,
.eiq-compare-final-card p,
.eiq-compare-final__empty {
  margin: 8px 0 0;
  color: var(--edgeiq-text-secondary, #5f6f82);
  line-height: 1.45;
}

.eiq-compare-final__header aside {
  min-width: 180px;
  padding-left: 18px;
  border-left: 1px solid var(--edgeiq-border, #d9e2ec);
}

.eiq-compare-final__header aside strong {
  font-size: 18px;
}

.eiq-compare-final__header small {
  display: block;
  margin-top: 4px;
  color: var(--edgeiq-text-secondary, #5f6f82);
}

.eiq-compare-final__controls {
  display: grid;
  grid-template-columns: 170px minmax(220px, 1fr) minmax(220px, 1fr) 190px;
  gap: 12px;
  padding: 14px;
}

.eiq-compare-final__controls label,
.eiq-compare-final__scope {
  display: grid;
  gap: 6px;
}

.eiq-compare-final__controls select {
  min-height: 38px;
  border: 1px solid var(--edgeiq-border, #d9e2ec);
  border-radius: 10px;
  background: #ffffff;
  color: var(--edgeiq-text-primary, #172033);
  font: inherit;
  padding: 0 12px;
}

.eiq-compare-final__scope strong {
  min-height: 38px;
  display: flex;
  align-items: center;
  border: 1px solid var(--edgeiq-border, #d9e2ec);
  border-radius: 10px;
  padding: 0 12px;
  background: var(--edgeiq-page-bg, #f5f8fb);
}

.eiq-compare-final__panels {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 320px;
  gap: 14px;
}

.eiq-compare-final-card {
  padding: 16px;
}

.eiq-compare-final-card > strong {
  display: block;
  margin-top: 6px;
  font-size: 20px;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-compare-final-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0 0;
}

.eiq-compare-final-card dl div {
  border: 1px solid var(--edgeiq-border, #d9e2ec);
  border-radius: 10px;
  padding: 10px;
  background: var(--edgeiq-page-bg, #f5f8fb);
}

.eiq-compare-final-card dt {
  color: var(--edgeiq-text-secondary, #5f6f82);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.eiq-compare-final-card dd {
  margin: 4px 0 0;
  font-weight: 800;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-compare-final__boundary ul {
  display: grid;
  gap: 10px;
  list-style: none;
  padding: 0;
  margin: 14px 0 0;
}

.eiq-compare-final__boundary li {
  display: grid;
  gap: 3px;
  border-top: 1px solid var(--edgeiq-border, #d9e2ec);
  padding-top: 10px;
}

.eiq-compare-final__boundary li b {
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-compare-final__boundary li em {
  color: var(--edgeiq-text-secondary, #5f6f82);
  font-style: normal;
  font-size: 12px;
  line-height: 1.35;
}

.eiq-compare-final-table {
  overflow: hidden;
}

.eiq-compare-final-table > header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--edgeiq-border, #d9e2ec);
}

.eiq-compare-final-table > header strong {
  color: var(--edgeiq-text-primary, #172033);
  font-size: 14px;
}

.eiq-compare-final-table > div {
  overflow-x: auto;
}

.eiq-compare-final-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.eiq-compare-final-table th,
.eiq-compare-final-table td {
  border-bottom: 1px solid var(--edgeiq-border, #d9e2ec);
  color: var(--edgeiq-text-primary, #172033);
  padding: 9px 12px;
  text-align: left;
  vertical-align: top;
}

.eiq-compare-final-table thead th {
  background: var(--edgeiq-page-bg, #f5f8fb);
  color: var(--edgeiq-text-secondary, #5f6f82);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.eiq-compare-final-table tbody th {
  width: 190px;
  color: var(--edgeiq-primary, #1167b1);
}

.eiq-compare-final__empty {
  padding: 16px;
}

@media (max-width: 1100px) {
  .eiq-compare-final__controls,
  .eiq-compare-final__panels {
    grid-template-columns: 1fr;
  }
}
'''

AUDIT = r'''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workspace = ROOT / "src/edgeiq-os/compare/CompareWorkspace.tsx"
service = ROOT / "src/edgeiq-os/compare/compareWorkspaceData.ts"
css = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"

required_workspace = [
    "Side-by-side governed comparison",
    "Common Metrics",
    "Historical Context",
    "Data Boundary",
    "Entity",
    "Left",
    "Right",
]
required_service = [
    "buildCompareViewModel",
    "getCompareOptions",
    "defaultCompareSelection",
    "Governed side-by-side jockey comparison is not available",
]
rejected_workspace = [
    "CompareService",
    "Similarity",
    "similarity",
    "verdict",
    "winner",
    "recommendation",
    "tip",
    "bet",
    "mock",
    "demo",
    "fake",
    "SpeedProfile",
    "TrackSignature",
    "RaceStrength",
    "RaceFlow",
]
rejected_product = [
    "Confidence",
    "confidence",
]

def fail(message: str) -> None:
    raise SystemExit(f"EDGEIQ_COMPARE_FINAL_SPEC_AUDIT_FAIL: {message}")

workspace_text = workspace.read_text(encoding="utf-8")
service_text = service.read_text(encoding="utf-8")
css_text = css.read_text(encoding="utf-8")

for token in required_workspace:
    if token not in workspace_text:
        fail(f"missing workspace token {token}")

for token in required_service:
    if token not in service_text:
        fail(f"missing service token {token}")

for token in rejected_workspace:
    if token in workspace_text:
        fail(f"rejected workspace token remains {token}")

visible_regions = workspace_text + "\n" + service_text
for token in rejected_product:
    if token in visible_regions:
        fail(f"rejected compare product term remains {token}")

if "eiq-compare-final" not in css_text:
    fail("missing compare final css")

if "var(--edgeiq-surface, #ffffff)" not in css_text:
    fail("compare css does not use white surface token")

report = ROOT / "docs/full-product-implementation/EDGEIQ_COMPARE_FINAL_SPEC_V1_AUDIT.md"
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(
    "\n".join(
        [
            "# EDGEiQ Compare Final Spec V1 Audit",
            "",
            "Status: EDGEIQ_COMPARE_FINAL_SPEC_AUDIT_PASS",
            "",
            "- Governed side-by-side comparison workspace present.",
            "- CompareService static model removed from product workspace.",
            "- Jockey, trainer and track comparison modes are not presented as supported where governed side-by-side feeds are unavailable.",
            "- Rejected product language was not found in Compare workspace/service.",
            "- White theme compare styling is present.",
            "",
        ]
    ),
    encoding="utf-8",
)
print("EDGEIQ_COMPARE_FINAL_SPEC_AUDIT_PASS")
'''

def write(path: str, text: str) -> None:
  target = ROOT / path
  target.parent.mkdir(parents=True, exist_ok=True)
  target.write_text(text, encoding="utf-8")

def append_once(path: str, marker: str, text: str) -> None:
  target = ROOT / path
  current = target.read_text(encoding="utf-8")
  if marker not in current:
    target.write_text(current.rstrip() + "\n" + text.lstrip(), encoding="utf-8")

write("src/edgeiq-os/compare/compareWorkspaceData.ts", COMPARE_SERVICE)
write("src/edgeiq-os/compare/CompareWorkspace.tsx", COMPARE_WORKSPACE)
append_once("src/edgeiq-os/styles/edgeiqOsV2.css", "EDGEIQ COMPARE FINAL SPEC V1", CSS_APPEND)
write("scripts/audit_edgeiq_compare_final_spec_v1.py", AUDIT)

print("EDGEIQ_COMPARE_FINAL_SPEC_APPLIED")
