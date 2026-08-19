import type {
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
