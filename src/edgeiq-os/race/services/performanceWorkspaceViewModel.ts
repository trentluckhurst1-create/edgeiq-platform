import type { BETA013Row, BETA013Start } from "./epiWorkspaceFeed";
import type { PerformanceIntelligenceRaceContext } from "../../services/performance-intelligence";

export type PerformanceHeatCell = {
  key: string;
  label: string;
  value: string;
  tileClass: "positive" | "neutral" | "negative" | "missing";
  context: Record<string, string>;
};

export type PerformanceHeatRow = {
  key: string;
  no: string;
  runner: string;
  silkUrl: string;
  epi: string;
  avg: string;
  last: string;
  current: string;
  peak: string;
  average: string;
  validStarts: number;
  cells: PerformanceHeatCell[];
};

export type PerformanceWorkspaceViewModel = {
  rows: PerformanceHeatRow[];
  sourceSummary: string;
  raceBenchmark: Array<{ label: string; value: string }>;
  historicalRuns: number;
};

function clean(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function cellFromStart(start: BETA013Start): PerformanceHeatCell {
  const context = start.context ?? null;
  return {
    key: start.key,
    label: start.key.replace("start_", "L"),
    value: clean(start.value),
    tileClass: start.value ? start.tileClass : "missing",
    context: {
      Date: clean(context?.DATE),
      Track: clean(context?.TRACK),
      Race: clean(context?.["MEETING / RACE"]),
      Distance: clean(context?.DISTANCE),
      Class: clean(context?.CLASS),
      Going: clean(context?.CONDITION),
      Barrier: clean(context?.BARRIER),
      Jockey: clean(context?.JOCKEY),
      Trainer: clean(context?.TRAINER),
      Position: clean(context?.FINISH),
      Margin: clean(context?.MARGIN),
      SP: clean(context?.SP),
      Rating: clean(context?.EPI),
    },
  };
}

export function buildPerformanceWorkspaceViewModel(
  rows: BETA013Row[],
  performanceContext: PerformanceIntelligenceRaceContext | null,
): PerformanceWorkspaceViewModel {
  const heatRows = rows.map((row) => {
    const cells = row.starts.filter((start) => clean(start.value) || start.context).slice(-5).map(cellFromStart);
    const last = [...cells].reverse().find((cell) => clean(cell.value))?.value ?? "";
    return {
      key: `${clean(row.no)}-${clean(row.horse)}`,
      no: clean(row.no),
      runner: clean(row.horse),
      silkUrl: "",
      epi: clean(row.current_epi),
      avg: clean(row.average_last_10),
      last,
      current: clean(row.current_epi),
      peak: clean(row.peak_last_10),
      average: clean(row.average_last_10),
      validStarts: row.starts.filter((start) => clean(start.value)).length,
      cells,
    };
  });

  const race = performanceContext?.race ?? null;
  return {
    rows: heatRows,
    sourceSummary: rows.length ? "Governed historical performance cells loaded." : "No governed historical performance cells supplied for this race.",
    historicalRuns: performanceContext?.historical.length ?? 0,
    raceBenchmark: [
      { label: "Benchmark Level", value: clean(race?.selected_benchmark_level) || "Unavailable" },
      { label: "Sample", value: clean(race?.selected_benchmark_sample_size) || "Unavailable" },
      { label: "Benchmark Time", value: clean(race?.benchmark_time_seconds) || "Unavailable" },
      { label: "Race vs Benchmark", value: clean(race?.seconds_vs_benchmark) || "Unavailable" },
    ],
  };
}
