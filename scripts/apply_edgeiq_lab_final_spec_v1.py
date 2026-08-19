from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "LabWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "labResearch.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"


SERVICE_TEXT = r'''import type {
  BenchmarkExplanationIndexRow,
  HorseIntelligenceIndexRow,
  PerformanceIntelligenceFeed,
  RaceIntelligenceIndexRow,
} from "../../services/performance-intelligence";

export type LabUniverse = "TODAY";
export type LabEntity = "HORSE" | "RACE" | "BENCHMARK" | "JOCKEY" | "TRAINER";
export type LabMetricKey =
  | "PERFORMANCE_COUNT"
  | "ELIGIBLE_PERFORMANCES"
  | "RUNNER_COUNT"
  | "BENCHMARK_SAMPLE"
  | "BENCHMARK_TIME"
  | "BENCHMARK_MEDIAN"
  | "BENCHMARK_MEAN"
  | "BENCHMARK_ELIGIBLE_SAMPLE";
export type LabSortDirection = "DESC" | "ASC";
export type LabGroupBy = "NONE" | "TRACK" | "RACE" | "CONDITION" | "CLASS";

export type LabOption<T extends string = string> = {
  value: T;
  label: string;
  disabled?: boolean;
  note?: string;
};

export type LabQuery = {
  universe: LabUniverse;
  track: string;
  scope: string;
  entity: LabEntity;
  metric: LabMetricKey;
  search: string;
  groupBy: LabGroupBy;
  sort: LabSortDirection;
  limit: number;
};

export type LabQueryModel = {
  universes: LabOption<LabUniverse>[];
  tracks: LabOption[];
  scopes: LabOption[];
  entities: LabOption<LabEntity>[];
  metricsByEntity: Record<LabEntity, LabOption<LabMetricKey>[]>;
  groupByOptions: LabOption<LabGroupBy>[];
  sortOptions: LabOption<LabSortDirection>[];
  limits: number[];
  summary: {
    races: number;
    horses: number;
    benchmarks: number;
    historical: number;
    generated: string;
    version: string;
  };
  limitations: string[];
};

export type LabResultRow = {
  id: string;
  values: Record<string, string>;
  sortValue: number;
};

export type LabQueryResult = {
  title: string;
  subtitle: string;
  columns: string[];
  rows: LabResultRow[];
  unavailableReason: string | null;
};

const unavailableResearchData = "Governed research data is not available for this module.";

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || text === "-" || text === "—") return "";
  if (["null", "undefined", "none", "n/a", "na"].includes(text.toLowerCase())) return "";
  return text;
}

function display(value: unknown, fallback = "Unavailable"): string {
  return clean(value) || fallback;
}

function numberValue(value: unknown): number {
  const parsed = Number(clean(value).replace(/[^\d.-]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function uniq(values: string[]): string[] {
  return [...new Set(values.map((value) => clean(value)).filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

function trackOptions(feed: PerformanceIntelligenceFeed): LabOption[] {
  const tracks = uniq(feed.race_intelligence_index.map((row) => row.track));
  return [{ value: "ALL", label: "All Tracks" }, ...tracks.map((track) => ({ value: track, label: track }))];
}

function metricOptions(entity: LabEntity): LabOption<LabMetricKey>[] {
  if (entity === "HORSE") {
    return [
      { value: "PERFORMANCE_COUNT", label: "Performance Count" },
      { value: "ELIGIBLE_PERFORMANCES", label: "Eligible Performances" },
    ];
  }
  if (entity === "RACE") {
    return [
      { value: "RUNNER_COUNT", label: "Runner Count" },
      { value: "BENCHMARK_SAMPLE", label: "Benchmark Sample Size" },
      { value: "BENCHMARK_TIME", label: "Benchmark Time" },
    ];
  }
  if (entity === "BENCHMARK") {
    return [
      { value: "BENCHMARK_SAMPLE", label: "Sample Size" },
      { value: "BENCHMARK_ELIGIBLE_SAMPLE", label: "Eligible Sample Size" },
      { value: "BENCHMARK_MEDIAN", label: "Median Time" },
      { value: "BENCHMARK_MEAN", label: "Mean Time" },
    ];
  }
  return [];
}

export function buildLabQueryModel(feed: PerformanceIntelligenceFeed): LabQueryModel {
  const counts = feed.manifest?.row_counts ?? {};
  return {
    universes: [{ value: "TODAY", label: "Today" }],
    tracks: trackOptions(feed),
    scopes: [{ value: "ALL_RACES", label: "All Races" }],
    entities: [
      { value: "HORSE", label: "Horse" },
      { value: "RACE", label: "Race" },
      { value: "BENCHMARK", label: "Benchmark" },
      { value: "JOCKEY", label: "Jockey", disabled: true, note: unavailableResearchData },
      { value: "TRAINER", label: "Trainer", disabled: true, note: unavailableResearchData },
    ],
    metricsByEntity: {
      HORSE: metricOptions("HORSE"),
      RACE: metricOptions("RACE"),
      BENCHMARK: metricOptions("BENCHMARK"),
      JOCKEY: [],
      TRAINER: [],
    },
    groupByOptions: [
      { value: "NONE", label: "No Grouping" },
      { value: "TRACK", label: "Track" },
      { value: "RACE", label: "Race" },
      { value: "CONDITION", label: "Condition" },
      { value: "CLASS", label: "Class" },
    ],
    sortOptions: [
      { value: "DESC", label: "Highest First" },
      { value: "ASC", label: "Lowest First" },
    ],
    limits: [3, 10, 25, 50],
    summary: {
      races: Number(counts.race_intelligence_index ?? feed.race_intelligence_index.length),
      horses: Number(counts.horse_intelligence_index ?? feed.horse_intelligence_index.length),
      benchmarks: Number(counts.benchmark_explanation_index ?? feed.benchmark_explanation_index.length),
      historical: Number(counts.historical_performance_intelligence_index ?? feed.historical_performance_intelligence_index.length),
      generated: display(feed.manifest?.generated_timestamp),
      version: display(feed.manifest?.feed_version, "v1"),
    },
    limitations: (feed.manifest?.known_limitations ?? []).map((item) => String(item)),
  };
}

function metricValue(row: HorseIntelligenceIndexRow | RaceIntelligenceIndexRow | BenchmarkExplanationIndexRow, metric: LabMetricKey): number {
  if (metric === "PERFORMANCE_COUNT") return numberValue((row as HorseIntelligenceIndexRow).performance_count);
  if (metric === "ELIGIBLE_PERFORMANCES") return numberValue((row as HorseIntelligenceIndexRow).eligible_performance_count);
  if (metric === "RUNNER_COUNT") return numberValue((row as RaceIntelligenceIndexRow).runner_count);
  if (metric === "BENCHMARK_SAMPLE") return numberValue((row as RaceIntelligenceIndexRow).selected_benchmark_sample_size ?? (row as BenchmarkExplanationIndexRow).sample_size);
  if (metric === "BENCHMARK_TIME") return numberValue((row as RaceIntelligenceIndexRow).benchmark_time_seconds);
  if (metric === "BENCHMARK_MEDIAN") return numberValue((row as BenchmarkExplanationIndexRow).median_time_seconds);
  if (metric === "BENCHMARK_MEAN") return numberValue((row as BenchmarkExplanationIndexRow).mean_time_seconds);
  if (metric === "BENCHMARK_ELIGIBLE_SAMPLE") return numberValue((row as BenchmarkExplanationIndexRow).eligible_sample_size);
  return 0;
}

function horseTrack(row: HorseIntelligenceIndexRow): string {
  return clean(row.track_profile).split(";")[0]?.split(":")[0] ?? "";
}

function rowTrack(row: HorseIntelligenceIndexRow | RaceIntelligenceIndexRow | BenchmarkExplanationIndexRow): string {
  return clean((row as RaceIntelligenceIndexRow).track) || horseTrack(row as HorseIntelligenceIndexRow);
}

function rowRace(row: HorseIntelligenceIndexRow | RaceIntelligenceIndexRow | BenchmarkExplanationIndexRow): string {
  return clean((row as HorseIntelligenceIndexRow).race_context_key ?? (row as RaceIntelligenceIndexRow).race_context_key);
}

function textMatches(values: unknown[], search: string): boolean {
  const needle = search.trim().toUpperCase();
  if (!needle) return true;
  return values.some((value) => clean(value).toUpperCase().includes(needle));
}

function filterRows<T extends HorseIntelligenceIndexRow | RaceIntelligenceIndexRow | BenchmarkExplanationIndexRow>(
  rows: T[],
  query: LabQuery,
  searchValues: (row: T) => unknown[],
): T[] {
  return rows.filter((row) => {
    const track = rowTrack(row);
    const trackOk = query.track === "ALL" || track.toUpperCase() === query.track.toUpperCase();
    return trackOk && textMatches(searchValues(row), query.search);
  });
}

function sortAndLimit(rows: LabResultRow[], query: LabQuery): LabResultRow[] {
  const direction = query.sort === "DESC" ? -1 : 1;
  return [...rows]
    .sort((left, right) => (left.sortValue - right.sortValue) * direction)
    .slice(0, query.limit);
}

function groupedRows(rows: LabResultRow[], query: LabQuery, metricLabel: string): LabResultRow[] {
  if (query.groupBy === "NONE") return rows;
  const groups = new Map<string, { rows: LabResultRow[]; total: number }>();
  for (const row of rows) {
    const key = display(row.values[query.groupBy], "Unassigned");
    const current = groups.get(key) ?? { rows: [], total: 0 };
    current.rows.push(row);
    current.total += row.sortValue;
    groups.set(key, current);
  }
  return sortAndLimit(
    [...groups.entries()].map(([key, group]) => ({
      id: key,
      sortValue: group.total,
      values: {
        GROUP: key,
        ROWS: String(group.rows.length),
        [`TOTAL ${metricLabel.toUpperCase()}`]: group.total.toFixed(1).replace(/\.0$/, ""),
        [`AVG ${metricLabel.toUpperCase()}`]: (group.total / Math.max(1, group.rows.length)).toFixed(1).replace(/\.0$/, ""),
      },
    })),
    query,
  );
}

export function metricLabelForQuery(model: LabQueryModel, query: LabQuery): string {
  return model.metricsByEntity[query.entity].find((item) => item.value === query.metric)?.label ?? query.metric;
}

export function executeLabResearchQuery(feed: PerformanceIntelligenceFeed, query: LabQuery): LabQueryResult {
  const model = buildLabQueryModel(feed);
  const metricLabel = metricLabelForQuery(model, query);
  if (!model.metricsByEntity[query.entity].some((metric) => metric.value === query.metric)) {
    return {
      title: `${query.entity} Research`,
      subtitle: "No governed metric is available for the selected entity.",
      columns: ["STATE"],
      rows: [],
      unavailableReason: unavailableResearchData,
    };
  }

  if (query.entity === "HORSE") {
    const sourceRows = filterRows(feed.horse_intelligence_index, query, (row) => [
      row.horse_name,
      row.race_context_key,
      row.track_profile,
      row.distance_profile,
      row.going_profile,
      row.class_profile,
      row.profile_quality_state,
    ]);
    const rows = sourceRows.map((row) => ({
      id: `${row.race_context_key}-${row.horse_code}-${row.horse_name}`,
      sortValue: metricValue(row, query.metric),
      values: {
        HORSE: display(row.horse_name),
        TRACK: display(rowTrack(row)),
        RACE: display(row.race_context_key),
        PROFILE: display(row.profile_quality_state).replace(/_/g, " "),
        "PERFORMANCE COUNT": display(row.performance_count, "0"),
        "ELIGIBLE PERFORMANCES": display(row.eligible_performance_count, "0"),
        "DATE RANGE": display(row.date_range),
        CONDITION: display(row.going_profile),
        CLASS: display(row.class_profile),
      },
    }));
    const resultRows = groupedRows(rows, query, metricLabel);
    return {
      title: "Horse Research",
      subtitle: `${resultRows.length} rows returned from governed horse research data.`,
      columns: query.groupBy === "NONE" ? ["HORSE", "TRACK", "RACE", "PROFILE", "PERFORMANCE COUNT", "ELIGIBLE PERFORMANCES", "DATE RANGE"] : Object.keys(resultRows[0]?.values ?? { GROUP: "", ROWS: "" }),
      rows: query.groupBy === "NONE" ? sortAndLimit(resultRows, query) : resultRows,
      unavailableReason: null,
    };
  }

  if (query.entity === "RACE") {
    const sourceRows = filterRows(feed.race_intelligence_index, query, (row) => [
      row.meeting,
      row.track,
      row.race_name,
      row.race_number,
      row.race_class,
      row.track_condition,
      row.race_quality_state,
    ]);
    const rows = sourceRows.map((row) => ({
      id: row.race_context_key,
      sortValue: metricValue(row, query.metric),
      values: {
        RACE: `R${display(row.race_number, "")}`,
        TRACK: display(row.track),
        NAME: display(row.race_name),
        DISTANCE: clean(row.distance_metres) ? `${row.distance_metres}m` : "Unavailable",
        CLASS: display(row.race_class),
        CONDITION: display(row.track_condition),
        "RUNNER COUNT": display(row.runner_count, "0"),
        "BENCHMARK SAMPLE": display(row.selected_benchmark_sample_size, "0"),
        "BENCHMARK TIME": display(row.benchmark_time_seconds),
      },
    }));
    const resultRows = groupedRows(rows, query, metricLabel);
    return {
      title: "Race Research",
      subtitle: `${resultRows.length} rows returned from governed race research data.`,
      columns: query.groupBy === "NONE" ? ["RACE", "TRACK", "NAME", "DISTANCE", "CLASS", "CONDITION", "RUNNER COUNT", "BENCHMARK SAMPLE", "BENCHMARK TIME"] : Object.keys(resultRows[0]?.values ?? { GROUP: "", ROWS: "" }),
      rows: query.groupBy === "NONE" ? sortAndLimit(resultRows, query) : resultRows,
      unavailableReason: null,
    };
  }

  if (query.entity === "BENCHMARK") {
    const sourceRows = filterRows(feed.benchmark_explanation_index, query, (row) => [
      row.track,
      row.course,
      row.distance_metres,
      row.race_class_canonical,
      row.going_canonical,
      row.benchmark_level,
    ]);
    const rows = sourceRows.map((row) => ({
      id: row.benchmark_id,
      sortValue: metricValue(row, query.metric),
      values: {
        TRACK: display(row.track),
        DISTANCE: clean(row.distance_metres) ? `${row.distance_metres}m` : "Unavailable",
        CLASS: display(row.race_class_canonical),
        CONDITION: display(row.going_canonical),
        LEVEL: display(row.benchmark_level),
        "SAMPLE SIZE": display(row.sample_size, "0"),
        "ELIGIBLE SAMPLE": display(row.eligible_sample_size, "0"),
        "MEDIAN TIME": display(row.median_time_seconds),
        "MEAN TIME": display(row.mean_time_seconds),
      },
    }));
    const resultRows = groupedRows(rows, query, metricLabel);
    return {
      title: "Benchmark Research",
      subtitle: `${resultRows.length} rows returned from governed benchmark research data.`,
      columns: query.groupBy === "NONE" ? ["TRACK", "DISTANCE", "CLASS", "CONDITION", "LEVEL", "SAMPLE SIZE", "ELIGIBLE SAMPLE", "MEDIAN TIME", "MEAN TIME"] : Object.keys(resultRows[0]?.values ?? { GROUP: "", ROWS: "" }),
      rows: query.groupBy === "NONE" ? sortAndLimit(resultRows, query) : resultRows,
      unavailableReason: null,
    };
  }

  return {
    title: `${query.entity} Research`,
    subtitle: "No governed metric is available for the selected entity.",
    columns: ["STATE"],
    rows: [],
    unavailableReason: unavailableResearchData,
  };
}
'''


COMPONENT_TEXT = r'''import { useEffect, useMemo, useState } from "react";
import {
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceFeed,
} from "../../services/performance-intelligence";
import {
  buildLabQueryModel,
  executeLabResearchQuery,
  type LabEntity,
  type LabGroupBy,
  type LabMetricKey,
  type LabQuery,
  type LabSortDirection,
  type LabUniverse,
} from "../services/labResearch";

function display(value: unknown, fallback = "Unavailable"): string {
  const text = String(value ?? "").trim();
  return text && text !== "-" ? text : fallback;
}

function initialQuery(): LabQuery {
  return {
    universe: "TODAY",
    track: "ALL",
    scope: "ALL_RACES",
    entity: "HORSE",
    metric: "PERFORMANCE_COUNT",
    search: "",
    groupBy: "NONE",
    sort: "DESC",
    limit: 25,
  };
}

function metricForEntity(entity: LabEntity): LabMetricKey {
  if (entity === "RACE") return "RUNNER_COUNT";
  if (entity === "BENCHMARK") return "BENCHMARK_SAMPLE";
  return "PERFORMANCE_COUNT";
}

function LabSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string; disabled?: boolean; note?: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="eiq-lab-final-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value as T)}>
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}{option.disabled && option.note ? ` - ${option.note}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

export function LabWorkspace() {
  const [feed, setFeed] = useState<PerformanceIntelligenceFeed | null>(null);
  const [pendingQuery, setPendingQuery] = useState<LabQuery>(() => initialQuery());
  const [activeQuery, setActiveQuery] = useState<LabQuery>(() => initialQuery());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadPerformanceIntelligenceFeed()
      .then((nextFeed) => {
        if (cancelled) return;
        setFeed(nextFeed);
        setError(null);
      })
      .catch((loadError) => {
        if (cancelled) return;
        setFeed(null);
        setError(loadError instanceof Error ? loadError.message : "LAB research data failed to load");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const model = useMemo(() => (feed ? buildLabQueryModel(feed) : null), [feed]);
  const result = useMemo(() => (feed ? executeLabResearchQuery(feed, activeQuery) : null), [activeQuery, feed]);

  if (loading) {
    return (
      <section className="eiq-lab-workspace eiq-lab-final">
        <div className="eiq-lab-empty">Loading LAB research data.</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="eiq-lab-workspace eiq-lab-final">
        <div className="eiq-lab-empty">{error}</div>
      </section>
    );
  }

  if (!feed || !model || !result) {
    return (
      <section className="eiq-lab-workspace eiq-lab-final">
        <div className="eiq-lab-empty">LAB research data is unavailable.</div>
      </section>
    );
  }

  const entityMetrics = model.metricsByEntity[pendingQuery.entity];
  const groupOptions = model.groupByOptions.filter((option) => {
    if (option.value === "RACE" && pendingQuery.entity === "BENCHMARK") return false;
    if (option.value === "CONDITION" && pendingQuery.entity === "HORSE") return true;
    return true;
  });

  return (
    <section className="eiq-lab-workspace eiq-lab-final" aria-label="LAB workspace">
      <header className="eiq-lab-final-hero">
        <div>
          <span>LAB</span>
          <h3>Racing Research Laboratory</h3>
          <p>Build governed racing research queries across the browser-safe product intelligence set.</p>
        </div>
        <dl>
          <div><dt>Races</dt><dd>{model.summary.races}</dd></div>
          <div><dt>Horses</dt><dd>{model.summary.horses}</dd></div>
          <div><dt>Benchmarks</dt><dd>{model.summary.benchmarks}</dd></div>
          <div><dt>Historical Rows</dt><dd>{model.summary.historical}</dd></div>
        </dl>
      </header>

      <section className="eiq-lab-final-builder" aria-label="Research query builder">
        <div className="eiq-lab-final-builder-grid">
          <LabSelect<LabUniverse> label="Universe" value={pendingQuery.universe} options={model.universes} onChange={(universe) => setPendingQuery((query) => ({ ...query, universe }))} />
          <LabSelect<string> label="Track" value={pendingQuery.track} options={model.tracks} onChange={(track) => setPendingQuery((query) => ({ ...query, track }))} />
          <LabSelect<string> label="Scope" value={pendingQuery.scope} options={model.scopes} onChange={(scope) => setPendingQuery((query) => ({ ...query, scope }))} />
          <LabSelect<LabEntity>
            label="Entity"
            value={pendingQuery.entity}
            options={model.entities}
            onChange={(entity) =>
              setPendingQuery((query) => ({
                ...query,
                entity,
                metric: metricForEntity(entity),
                groupBy: "NONE",
              }))
            }
          />
          <LabSelect<LabMetricKey> label="Metric" value={pendingQuery.metric} options={entityMetrics} onChange={(metric) => setPendingQuery((query) => ({ ...query, metric }))} />
          <LabSelect<LabGroupBy> label="Group By" value={pendingQuery.groupBy} options={groupOptions} onChange={(groupBy) => setPendingQuery((query) => ({ ...query, groupBy }))} />
          <LabSelect<LabSortDirection> label="Sort" value={pendingQuery.sort} options={model.sortOptions} onChange={(sort) => setPendingQuery((query) => ({ ...query, sort }))} />
          <label className="eiq-lab-final-field">
            <span>Result Limit</span>
            <select value={pendingQuery.limit} onChange={(event) => setPendingQuery((query) => ({ ...query, limit: Number(event.target.value) }))}>
              {model.limits.map((limit) => (
                <option key={limit} value={limit}>{limit}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="eiq-lab-final-filterbar">
          <label>
            <span>Filter</span>
            <input
              value={pendingQuery.search}
              onChange={(event) => setPendingQuery((query) => ({ ...query, search: event.target.value }))}
              placeholder="Horse, track, race, class or condition"
            />
          </label>
          <button type="button" onClick={() => setActiveQuery(pendingQuery)}>Run Query</button>
        </div>
      </section>

      <div className="eiq-lab-final-layout">
        <main className="eiq-lab-final-results">
          <section className="eiq-lab-panel eiq-lab-panel--wide">
            <header>
              <span>{result.title}</span>
              <small>{result.subtitle}</small>
            </header>
            {result.unavailableReason ? (
              <div className="eiq-lab-empty">{result.unavailableReason}</div>
            ) : result.rows.length ? (
              <div className="eiq-lab-final-table-scroll">
                <table className="eiq-lab-table">
                  <thead>
                    <tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row) => (
                      <tr key={row.id}>
                        {result.columns.map((column) => (
                          <td key={`${row.id}-${column}`}>{display(row.values[column])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="eiq-lab-empty">No rows match the selected governed query.</div>
            )}
          </section>
        </main>
        <aside className="eiq-lab-final-side">
          <section className="eiq-lab-panel">
            <header><span>Research Boundary</span></header>
            <p className="eiq-lab-copy">LAB only exposes metrics supplied by the governed product intelligence set. Jockey and trainer modules remain inactive until a governed research dataset is available.</p>
          </section>
          <section className="eiq-lab-panel">
            <header><span>Query Scope</span></header>
            <dl className="eiq-lab-final-scope">
              <div><dt>Universe</dt><dd>{activeQuery.universe}</dd></div>
              <div><dt>Track</dt><dd>{activeQuery.track === "ALL" ? "All Tracks" : activeQuery.track}</dd></div>
              <div><dt>Entity</dt><dd>{activeQuery.entity}</dd></div>
              <div><dt>Metric</dt><dd>{model.metricsByEntity[activeQuery.entity].find((item) => item.value === activeQuery.metric)?.label ?? activeQuery.metric}</dd></div>
              <div><dt>Generated</dt><dd>{model.summary.generated}</dd></div>
            </dl>
          </section>
          {model.limitations.length ? (
            <section className="eiq-lab-panel">
              <header><span>Data Limits</span></header>
              <ul className="eiq-lab-final-list">
                {model.limitations.slice(0, 4).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
'''


def patch_css() -> None:
  css = CSS.read_text(encoding="utf-8")
  block = r'''

/* EDGEIQ LAB FINAL SPEC V1 */
.eiq-lab-final {
  display: grid;
  gap: 14px;
}

.eiq-lab-final-hero,
.eiq-lab-final-builder,
.eiq-lab-final .eiq-lab-panel {
  border: 1px solid #e5e8ee;
  border-radius: 14px;
  background: #ffffff;
}

.eiq-lab-final-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 16px;
}

.eiq-lab-final-hero span,
.eiq-lab-final .eiq-lab-panel > header span,
.eiq-lab-final-field span,
.eiq-lab-final-filterbar span,
.eiq-lab-final-scope dt {
  color: #1f5fd6;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.eiq-lab-final-hero h3 {
  margin: 4px 0 0;
  color: #172033;
  font-size: 22px;
  font-weight: 800;
}

.eiq-lab-final-hero p {
  margin: 6px 0 0;
  color: #5c6675;
  font-size: 13px;
}

.eiq-lab-final-hero dl {
  display: grid;
  grid-template-columns: repeat(4, minmax(95px, 1fr));
  gap: 8px;
  margin: 0;
  min-width: min(520px, 100%);
}

.eiq-lab-final-hero dl div {
  border: 1px solid #e5e8ee;
  border-radius: 10px;
  padding: 10px;
  background: #fafbfc;
}

.eiq-lab-final-hero dt {
  color: #7c8798;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.eiq-lab-final-hero dd {
  margin: 4px 0 0;
  color: #172033;
  font-size: 17px;
  font-weight: 800;
}

.eiq-lab-final-builder {
  padding: 14px;
}

.eiq-lab-final-builder-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 10px;
}

.eiq-lab-final-field,
.eiq-lab-final-filterbar label {
  display: grid;
  gap: 6px;
}

.eiq-lab-final-field select,
.eiq-lab-final-filterbar input {
  width: 100%;
  min-height: 36px;
  border: 1px solid #d7dce5;
  border-radius: 10px;
  background: #ffffff;
  color: #172033;
  padding: 0 10px;
  font-size: 13px;
  font-weight: 650;
}

.eiq-lab-final-filterbar {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto;
  gap: 10px;
  align-items: end;
  margin-top: 12px;
}

.eiq-lab-final-filterbar button {
  min-height: 36px;
  border: 1px solid #1f5fd6;
  border-radius: 10px;
  background: #1f5fd6;
  color: #ffffff;
  padding: 0 16px;
  font-size: 12px;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: .06em;
}

.eiq-lab-final-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 14px;
  align-items: start;
}

.eiq-lab-final .eiq-lab-panel > header {
  padding: 12px 14px;
  border-bottom: 1px solid #e5e8ee;
  background: #fafbfc;
  border-radius: 14px 14px 0 0;
}

.eiq-lab-final .eiq-lab-panel > header small {
  display: block;
  margin-top: 4px;
  color: #5c6675;
  font-size: 12px;
}

.eiq-lab-final-table-scroll {
  width: 100%;
  overflow-x: auto;
}

.eiq-lab-final-side {
  display: grid;
  gap: 14px;
}

.eiq-lab-final-scope {
  display: grid;
  margin: 0;
  padding: 10px 14px;
}

.eiq-lab-final-scope div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #e5e8ee;
}

.eiq-lab-final-scope dd {
  margin: 0;
  color: #172033;
  font-size: 12px;
  font-weight: 760;
  text-align: right;
}

.eiq-lab-final-list {
  margin: 0;
  padding: 12px 16px 14px 28px;
  color: #3c4656;
  font-size: 12px;
  line-height: 1.45;
}

@media (max-width: 1200px) {
  .eiq-lab-final-layout,
  .eiq-lab-final-hero {
    display: grid;
    grid-template-columns: 1fr;
  }

  .eiq-lab-final-builder-grid {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
}
'''
  marker = "/* EDGEIQ LAB FINAL SPEC V1 */"
  if marker in css:
    start = css.index(marker)
    css = css[:start].rstrip() + "\n" + block
  else:
    css = css.rstrip() + "\n" + block
  CSS.write_text(css, encoding="utf-8")


def main() -> int:
  SERVICE.write_text(SERVICE_TEXT, encoding="utf-8")
  COMPONENT.write_text(COMPONENT_TEXT, encoding="utf-8")
  patch_css()
  print("EDGEIQ_LAB_FINAL_SPEC_V1_APPLIED")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
