from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT_LABEL = f"CHECKPOINT_RACE_FIELD_PERFORMANCE_EPI_TRANCHE_V1_{STAMP}"
CHECKPOINT_DIR = ROOT / "docs" / "full-product-implementation" / "checkpoints" / CHECKPOINT_LABEL
DOC_DIR = ROOT / "docs" / "full-product-implementation"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def checkpoint(path: Path) -> None:
    if path.exists():
        target = CHECKPOINT_DIR / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def replace_once(path: Path, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"Expected block not found in {path}: {old[:120]}")
    write(path, text.replace(old, new, 1))


def append_once(path: Path, marker: str, block: str) -> None:
    text = read(path)
    if marker in text:
        return
    write(path, text.rstrip() + "\n\n" + block.strip() + "\n")


def csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def csv_headers(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def json_summary(path: Path) -> tuple[int, list[str]]:
    if not path.exists():
        return 0, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("races"), list):
        keys = sorted({key for race in payload["races"][:20] if isinstance(race, dict) for key in race.keys()})
        return len(payload["races"]), keys
    if isinstance(payload, list):
        keys = sorted({key for row in payload[:20] if isinstance(row, dict) for key in row.keys()})
        return len(payload), keys
    return 1, sorted(payload.keys()) if isinstance(payload, dict) else []


def write_trace() -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    data = ROOT / "public" / "data"
    performance_json = ROOT / "public" / "performance-intelligence" / "edgeiq_performance_intelligence_product_feeds_v1.json"
    current_json = data / "edgeiq_current_race_intelligence_v1.json"

    current_count, current_keys = json_summary(current_json)
    performance_count, performance_keys = json_summary(performance_json)
    epi_headers = csv_headers(data / "edgeiq_epi_workspace_terminal_feed_v1.csv")
    form_count, form_keys = json_summary(data / "edgeiq_form_guide_enriched_v2.json")

    rows = [
        ("Runner identity", "RaceBook field + FormGuide normaliser", "official.number, runnerNumber, saddlecloth, no, runner/horse/name"),
        ("Saddlecloth", "RaceBook field + FormGuide normaliser", "number, runnerNumber, saddlecloth; rendered as text plus silk image only"),
        ("Silks", "RaceBook field + FormGuide normaliser", "official.silkUrl, silkUrl, silksUrl, silk"),
        ("Barrier", "RaceBook field + FormGuide normaliser", "official.barrier, barrier, bar, draw"),
        ("Weight", "RaceBook field + FormGuide normaliser", "official.weight, weight, wt"),
        ("Jockey", "RaceBook field + FormGuide normaliser", "official.jockey, jockey"),
        ("Trainer", "RaceBook field + FormGuide normaliser", "official.trainer, trainer"),
        ("Market", "Current race intelligence + FormGuide + field", "market.value, marketPrice, official.market, price"),
        ("EDGEiQ price", "Current race intelligence + FormGuide", "edgeiqPrice.value, edgeiqPrice"),
        ("EPI", "EPI workspace terminal + current race intelligence + FormGuide", "current_epi, epi.value, epi"),
        ("EPI speed", "Current race intelligence + FormGuide", "earlySpeed.value, earlySpeed"),
        ("Status", "RaceBook field + current race intelligence", "scratched/status fields"),
        ("Historical runs", "FormGuide enriched feed", "recentRuns/fullForm/lastFive"),
        ("Historical performance rating", "EPI terminal start cells with performance-intelligence run context", "start_10..start_1 + *_context"),
    ]

    trace_lines = [
        "# EDGEIQ RACE/FIELD/PERFORMANCE/EPI Trace V1",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Source Flow",
        "",
        "| Field | Canonical display source | Current columns / keys |",
        "| --- | --- | --- |",
    ]
    trace_lines.extend(f"| {field} | {source} | {columns} |" for field, source, columns in rows)
    trace_lines.extend(
        [
            "",
            "## Feed Coverage Snapshot",
            "",
            f"- edgeiq_current_race_intelligence_v1.json races: {current_count}; keys sampled: {', '.join(current_keys[:24])}",
            f"- edgeiq_form_guide_enriched_v2.json races: {form_count}; keys sampled: {', '.join(form_keys[:24])}",
            f"- edgeiq_epi_workspace_terminal_feed_v1.csv columns sampled: {', '.join(epi_headers[:32])}",
            f"- performance-intelligence product feed object count: {performance_count}; keys sampled: {', '.join(performance_keys[:24])}",
            "",
            "## Component Flow",
            "",
            "- RaceFileV3 maps global RACE to RaceWorkspace tab RACE.",
            "- RaceWorkspace orchestrates RaceIntelligenceWorkspace, FieldWorkspace, PerformanceWorkspace and EpiWorkspaceWorkspace.",
            "- RaceIntelligenceWorkspace renders a service-built model from raceBook, formGuide and current race intelligence.",
            "- FieldWorkspace renders a service-built field model with optional governed recent form expansion.",
            "- PerformanceWorkspace renders historical performance heat map rows; run metadata is supplied by the performance-intelligence service and historical rating cells by the governed EPI terminal feed.",
            "- EpiWorkspaceWorkspace remains the dedicated current EDGEIQ Performance Index workspace.",
            "",
            "## Mock / Demo Risk Trace",
            "",
            "- No product-facing rows are generated from demo, sample, mock, or synthetic arrays by this tranche.",
            "- Unavailable governed values render as unavailable/pending states rather than invented metrics.",
        ]
    )
    write(DOC_DIR / "EDGEIQ_RACE_FIELD_PERFORMANCE_EPI_TRACE_V1.md", "\n".join(trace_lines) + "\n")


CURRENT_RACE_INTELLIGENCE_FEED = r'''export type CurrentRaceIntelligenceRunner = {
  runnerId?: string | number | null;
  runnerNumber?: string | number | null;
  runnerName?: string | null;
  scratched?: boolean | null;
  barrier?: string | number | null;
  market?: { value?: string | number | null; asAt?: string | null } | null;
  edgeiqPrice?: { value?: string | number | null; asAt?: string | null } | null;
  epi?: {
    value?: string | number | null;
    display?: string | null;
    status?: string | null;
    rankInRace?: string | number | null;
    activeFieldSize?: string | number | null;
    fieldAverage?: string | number | null;
    differenceFromFieldAverage?: string | number | null;
  } | null;
  earlySpeed?: { value?: string | number | null } | null;
  lateSpeed?: { value?: string | number | null } | null;
  suitability?: { value?: string | number | null; band?: string | null; publicReasons?: string[] | null } | null;
  formMomentum?: { value?: string | number | null; band?: string | null; publicReasons?: string[] | null } | null;
  raceShape?: { value?: string | number | null } | null;
  projectedMapZone?: string | null;
  publicReasons?: Record<string, string[] | null | undefined> | null;
};

export type CurrentRaceIntelligenceRace = {
  raceDate?: string | null;
  meeting?: string | null;
  raceNumber?: string | number | null;
  raceKey?: string | null;
  raceName?: string | null;
  distance?: string | number | null;
  class?: string | null;
  trackCondition?: string | null;
  rail?: string | null;
  weather?: string | null;
  tempo?: string | null;
  pressure?: string | null;
  mapCoverage?: { count?: number | null; average?: number | null; top?: number | null } | null;
  fieldSummary?: {
    epi?: { count?: number | null; average?: number | null; top?: number | null } | null;
    earlySpeed?: { count?: number | null; average?: number | null; top?: number | null } | null;
    lateSpeed?: { count?: number | null; average?: number | null; top?: number | null } | null;
    topEpi?: Array<{ runnerNumber?: string | number | null; runnerName?: string | null; value?: string | number | null }> | null;
  } | null;
  overview?: {
    statements?: Array<{ statement?: string | null; source?: string | null }> | null;
  } | null;
  runners?: CurrentRaceIntelligenceRunner[] | null;
};

type CurrentRaceIntelligencePayload = {
  schemaVersion?: string;
  generatedAt?: string;
  races?: CurrentRaceIntelligenceRace[];
};

const URL = "/data/edgeiq_current_race_intelligence_v1.json";
const MAX_RACES = 1000;
let cachedPayload: CurrentRaceIntelligencePayload | null = null;
let pendingPayload: Promise<CurrentRaceIntelligencePayload> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function raceKeyCandidates(raceKey: string | null | undefined): string[] {
  const text = usable(raceKey);
  if (!text) return [];
  const upper = text.toUpperCase();
  const candidates = [upper];
  const pipeMatch = upper.match(/^(\d{4}-\d{2}-\d{2})\|(.+)\|R?(\d+)$/);
  if (pipeMatch) candidates.push(`${pipeMatch[1]}|${pipeMatch[2]}|${pipeMatch[3]}`);
  const underscoreMatch = upper.match(/^(\d{4}-\d{2}-\d{2})_(.+)_R?(\d+)$/);
  if (underscoreMatch) {
    candidates.push(`${underscoreMatch[1]}|${underscoreMatch[2]}|${underscoreMatch[3]}`);
    candidates.push(`${underscoreMatch[1]}|${underscoreMatch[2]}|R${underscoreMatch[3]}`);
  }
  return [...new Set(candidates)];
}

function normaliseRaceKey(value: unknown): string {
  return usable(value).toUpperCase().replace(/_R(\d+)$/, "|R$1").replace(/_/g, "|");
}

export async function loadCurrentRaceIntelligenceFeed(force = false): Promise<CurrentRaceIntelligencePayload> {
  if (!force && cachedPayload) return cachedPayload;
  if (pendingPayload) return pendingPayload;
  pendingPayload = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Current race intelligence feed failed with ${response.status}`);
      const payload = (await response.json()) as CurrentRaceIntelligencePayload;
      if ((payload.races?.length ?? 0) > MAX_RACES) {
        console.warn("EDGEiQ rejected oversized current race intelligence feed", payload.races?.length);
        return { ...payload, races: [] };
      }
      return payload;
    })
    .then((payload) => {
      cachedPayload = payload;
      return payload;
    })
    .finally(() => {
      pendingPayload = null;
    });
  return pendingPayload;
}

export function findCurrentRaceIntelligenceRace(
  payload: CurrentRaceIntelligencePayload | null | undefined,
  raceKey: string | null | undefined,
): CurrentRaceIntelligenceRace | null {
  const candidates = raceKeyCandidates(raceKey);
  if (!payload?.races?.length || !candidates.length) return null;
  return payload.races.find((race) => candidates.includes(normaliseRaceKey(race.raceKey))) ?? null;
}
'''


RACE_WORKSPACE_VIEW_MODEL = r'''import type { FormGuideRaceDisplay, FormGuideRunnerDisplay } from "./formGuideNormaliser";
import type { CurrentRaceIntelligenceRace, CurrentRaceIntelligenceRunner } from "./currentRaceIntelligenceFeed";

export type RaceRunnerBoardRow = {
  no: string;
  silkUrl: string;
  runner: string;
  barrier: string;
  weight: string;
  jockey: string;
  trainer: string;
  epiSpeed: string;
  edgeiq: string;
  market: string;
  status: string;
};

export type RaceIntelligenceCard = {
  label: string;
  value: string;
  detail: string;
};

export type RaceIntelligenceViewModel = {
  cards: RaceIntelligenceCard[];
  whatMatters: string[];
  speedMap: Array<{ zone: string; runners: string[] }>;
  topEpi: Array<{ no: string; runner: string; value: string }>;
  runnerBoard: RaceRunnerBoardRow[];
  marketSnapshot: Array<{ label: string; value: string }>;
  unavailable: string[];
};

function clean(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function firstValue(source: unknown, keys: string[]): unknown {
  if (!source || typeof source !== "object") return undefined;
  for (const key of keys) {
    const value = key.split(".").reduce((acc: any, part) => acc?.[part], source as any);
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return undefined;
}

function price(value: unknown): string {
  const text = clean(value).replace(/[$,]/g, "");
  const number = Number(text);
  if (!Number.isFinite(number) || number <= 0) return "";
  return `$${number.toFixed(2)}`;
}

function numberText(value: unknown, decimals = 1): string {
  const text = clean(value);
  if (!text) return "";
  const number = Number(text);
  if (!Number.isFinite(number)) return text;
  return number.toFixed(decimals);
}

function normaliseRunner(value: unknown): string {
  return clean(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function intelligenceRunnerFor(race: CurrentRaceIntelligenceRace | null, no: string, runner: string): CurrentRaceIntelligenceRunner | null {
  if (!race?.runners?.length) return null;
  const runnerKey = normaliseRunner(runner);
  return (
    race.runners.find((item) => clean(item.runnerNumber) === no) ??
    race.runners.find((item) => runnerKey && normaliseRunner(item.runnerName) === runnerKey) ??
    null
  );
}

function rowFromFormRunner(runner: FormGuideRunnerDisplay, intelligence: CurrentRaceIntelligenceRunner | null): RaceRunnerBoardRow {
  const marketValue = price(intelligence?.market?.value) || runner.marketPrice;
  const edgeiqValue = price(intelligence?.edgeiqPrice?.value) || runner.edgeiqPrice || numberText(intelligence?.epi?.display ?? intelligence?.epi?.value) || runner.epi;
  return {
    no: runner.no,
    silkUrl: runner.silkUrl,
    runner: runner.horse,
    barrier: runner.barrier,
    weight: runner.weight,
    jockey: runner.jockey,
    trainer: runner.trainer,
    epiSpeed: numberText(intelligence?.earlySpeed?.value, 0) || runner.earlySpeed,
    edgeiq: edgeiqValue,
    market: marketValue || "Pending Market",
    status: runner.scratched || intelligence?.scratched ? "Scratched" : "Active",
  };
}

function rowFromRawRunner(row: any, index: number, race: CurrentRaceIntelligenceRace | null): RaceRunnerBoardRow {
  const no = clean(firstValue(row, ["official.number", "number", "runnerNumber", "saddlecloth", "no"])) || String(index + 1);
  const runner = clean(firstValue(row, ["official.runner", "runner", "runnerName", "horse", "name"]));
  const intelligence = intelligenceRunnerFor(race, no, runner);
  return {
    no,
    silkUrl: clean(firstValue(row, ["official.silkUrl", "silkUrl", "silksUrl", "silk"])),
    runner,
    barrier: clean(firstValue(row, ["official.barrier", "barrier", "bar", "draw"])),
    weight: clean(firstValue(row, ["official.weight", "weight", "wt"])),
    jockey: clean(firstValue(row, ["official.jockey", "jockey"])),
    trainer: clean(firstValue(row, ["official.trainer", "trainer"])),
    epiSpeed: numberText(intelligence?.earlySpeed?.value, 0),
    edgeiq: price(intelligence?.edgeiqPrice?.value) || numberText(intelligence?.epi?.display ?? intelligence?.epi?.value),
    market: price(intelligence?.market?.value) || "Pending Market",
    status: intelligence?.scratched ? "Scratched" : "Active",
  };
}

function buildBoard(field: any[], formGuide: FormGuideRaceDisplay | null | undefined, race: CurrentRaceIntelligenceRace | null): RaceRunnerBoardRow[] {
  if (formGuide?.runners?.length) {
    return formGuide.runners.map((runner) => rowFromFormRunner(runner, intelligenceRunnerFor(race, runner.no, runner.horse)));
  }
  return (Array.isArray(field) ? field : []).map((runner, index) => rowFromRawRunner(runner, index, race));
}

function topEpiFromRace(race: CurrentRaceIntelligenceRace | null, board: RaceRunnerBoardRow[]): RaceIntelligenceViewModel["topEpi"] {
  const supplied = race?.fieldSummary?.topEpi?.map((item) => ({
    no: clean(item.runnerNumber),
    runner: clean(item.runnerName),
    value: numberText(item.value),
  })).filter((item) => item.runner && item.value) ?? [];
  if (supplied.length) return supplied.slice(0, 3);

  return board
    .map((row) => ({ row, value: Number(row.edgeiq.replace(/[$,]/g, "")) }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, 3)
    .map((item) => ({ no: item.row.no, runner: item.row.runner, value: item.row.edgeiq }));
}

function speedMapFromRace(race: CurrentRaceIntelligenceRace | null): RaceIntelligenceViewModel["speedMap"] {
  const lanes = ["LEAD", "ON PACE", "MIDFIELD", "BACK", "UNRESOLVED"];
  const grouped = new Map<string, string[]>();
  lanes.forEach((lane) => grouped.set(lane, []));
  (race?.runners ?? []).forEach((runner) => {
    const zone = clean(runner.projectedMapZone).replace(/_/g, " ").toUpperCase() || "UNRESOLVED";
    const lane = lanes.includes(zone) ? zone : zone.includes("LEAD") ? "LEAD" : zone.includes("PACE") ? "ON PACE" : zone.includes("BACK") ? "BACK" : zone.includes("MID") ? "MIDFIELD" : "UNRESOLVED";
    const name = clean(runner.runnerName);
    if (name) grouped.get(lane)?.push(`${clean(runner.runnerNumber)} ${name}`.trim());
  });
  return lanes.map((zone) => ({ zone, runners: grouped.get(zone) ?? [] })).filter((item) => item.runners.length || item.zone !== "UNRESOLVED");
}

export function buildRaceIntelligenceViewModel(params: {
  raceBook: any;
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  intelligenceRace?: CurrentRaceIntelligenceRace | null;
}): RaceIntelligenceViewModel {
  const { raceBook, field, formGuide, intelligenceRace } = params;
  const official = raceBook?.official ?? {};
  const board = buildBoard(field, formGuide, intelligenceRace);
  const topEpi = topEpiFromRace(intelligenceRace ?? null, board);
  const statements = (intelligenceRace?.overview?.statements ?? [])
    .map((item) => clean(item.statement))
    .filter((statement) => statement && !statement.toLowerCase().includes("confidence"))
    .slice(0, 5);
  const unavailable: string[] = [];
  const tempo = clean(intelligenceRace?.tempo ?? intelligenceRace?.pressure ?? firstValue(official, ["tempo", "raceTempo"]));
  const epf = clean(firstValue(official, ["epf", "edgeiqPerformanceFigure"])) || (intelligenceRace?.fieldSummary?.epi?.average ? numberText(intelligenceRace.fieldSummary.epi.average) : "");
  const hiddenAngles = statements.length ? `${statements.length} supplied` : "";
  const determinant = topEpi[0]?.runner ?? "";
  if (!tempo) unavailable.push("Tempo feed not supplied for this race.");
  if (!epf) unavailable.push("EPF feed not supplied for this race.");
  if (!statements.length) unavailable.push("What Matters Today feed has no governed statements for this race.");

  return {
    cards: [
      { label: "Tempo", value: tempo || "Unavailable", detail: clean(intelligenceRace?.pressure) || "Governed race tempo feed" },
      { label: "EPF", value: epf || "Unavailable", detail: "Expected performance figure" },
      { label: "Key Determinants", value: determinant || "Unavailable", detail: topEpi.length ? "Top supplied EPI profile" : "Not supplied" },
      { label: "Hidden Angles", value: hiddenAngles || "Unavailable", detail: "Governed intelligence statements" },
    ],
    whatMatters: statements,
    speedMap: speedMapFromRace(intelligenceRace ?? null),
    topEpi,
    runnerBoard: board,
    marketSnapshot: [
      { label: "Favourite", value: board.find((row) => row.market && row.market !== "Pending Market")?.runner || "Pending Market" },
      { label: "Best EDGEiQ", value: topEpi[0]?.runner || "Unavailable" },
      { label: "Market", value: board.some((row) => row.market && row.market !== "Pending Market") ? "Available" : "Pending Market" },
    ],
    unavailable,
  };
}
'''


FIELD_WORKSPACE_VIEW_MODEL = r'''import type { FormGuideRaceDisplay, FormGuideRecentRun, FormGuideRunnerDisplay } from "./formGuideNormaliser";

export type FieldWorkspaceRow = {
  key: string;
  sourceIndex: number;
  no: string;
  silkUrl: string;
  runner: string;
  barrier: string;
  weight: string;
  jockey: string;
  trainer: string;
  edgeiq: string;
  market: string;
  status: string;
  recentRuns: FormGuideRecentRun[];
};

function clean(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function firstValue(row: any, keys: string[]): any {
  for (const key of keys) {
    const value = key.split(".").reduce((acc: any, part) => acc?.[part], row);
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return undefined;
}

function normaliseRunner(value: unknown): string {
  return clean(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function formatPrice(value: unknown): string {
  const text = clean(value).replace(/[$,]/g, "");
  const number = Number(text);
  if (!Number.isFinite(number) || number <= 0) return clean(value);
  return `$${number.toFixed(2)}`;
}

function matchFormRunner(formGuide: FormGuideRaceDisplay | null | undefined, no: string, runner: string): FormGuideRunnerDisplay | null {
  if (!formGuide?.runners?.length) return null;
  const runnerKey = normaliseRunner(runner);
  return (
    formGuide.runners.find((candidate) => clean(candidate.no) === no) ??
    formGuide.runners.find((candidate) => runnerKey && normaliseRunner(candidate.horse) === runnerKey) ??
    null
  );
}

function statusForRunner(row: any, formRunner: FormGuideRunnerDisplay | null): string {
  if (formRunner?.scratched) return "Scratched";
  const raw = clean(firstValue(row, ["status", "official.status", "scratchingStatus", "official.scratchingStatus"]));
  if (raw) return raw;
  const scratched = firstValue(row, ["scratched", "official.scratched", "isScratched"]);
  return scratched === true || String(scratched).toUpperCase() === "TRUE" ? "Scratched" : "Active";
}

export function buildFieldWorkspaceRows(params: {
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  weight: (value: any) => string;
  market: (value: any) => string;
}): FieldWorkspaceRow[] {
  const rows = Array.isArray(params.field) ? params.field : [];
  return rows.map((runner, index) => {
    const no = clean(firstValue(runner, ["official.number", "number", "runnerNumber", "saddlecloth", "no"])) || String(index + 1);
    const runnerName = clean(firstValue(runner, ["official.runner", "runner", "runnerName", "horse", "name"]));
    const formRunner = matchFormRunner(params.formGuide, no, runnerName);
    const status = statusForRunner(runner, formRunner);
    return {
      key: `${no}-${runnerName || formRunner?.horse || index}`,
      sourceIndex: index,
      no,
      silkUrl: formRunner?.silkUrl || clean(firstValue(runner, ["official.silkUrl", "silkUrl", "silksUrl", "silk"])),
      runner: formRunner?.horse || runnerName,
      barrier: formRunner?.barrier || clean(firstValue(runner, ["official.barrier", "barrier", "bar", "draw"])),
      weight: formRunner?.weight || params.weight(firstValue(runner, ["official.weight", "weight", "wt"])),
      jockey: formRunner?.jockey || clean(firstValue(runner, ["official.jockey", "jockey"])),
      trainer: formRunner?.trainer || clean(firstValue(runner, ["official.trainer", "trainer"])),
      edgeiq: formRunner?.epi || clean(firstValue(runner, ["metrics.epi", "epi", "currentEpi", "rating", "official.epi"])),
      market: formRunner?.marketPrice || params.market(firstValue(runner, ["official.market", "market", "live", "price"])) || (status === "Scratched" ? "" : "Pending Market"),
      status,
      recentRuns: (formRunner?.recentRuns ?? []).slice(0, 5),
    };
  });
}
'''


PERFORMANCE_WORKSPACE_VIEW_MODEL = r'''import type { BETA013Row, BETA013Start } from "./epiWorkspaceFeed";
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
    return {
      key: `${clean(row.no)}-${clean(row.horse)}`,
      no: clean(row.no),
      runner: clean(row.horse),
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
'''


RACE_INTELLIGENCE_WORKSPACE = r'''import { useEffect, useMemo, useState } from "react";
import { buildRaceIntelligenceViewModel } from "../services/raceWorkspaceViewModel";
import {
  findCurrentRaceIntelligenceRace,
  loadCurrentRaceIntelligenceFeed,
  type CurrentRaceIntelligenceRace,
} from "../services/currentRaceIntelligenceFeed";
import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";

type RaceIntelligenceWorkspaceProps = {
  raceBook: any;
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  raceKey?: string | null;
  clean: (value: any) => string;
};

function display(value: string): string {
  return value || "Unavailable";
}

function Silk({ src, runner }: { src: string; runner: string }) {
  return src ? <img className="eiq-race-intel-silk" src={src} alt={`${runner} silks`} loading="lazy" /> : <span className="eiq-race-intel-silk eiq-race-intel-silk--empty" aria-hidden="true" />;
}

export function RaceIntelligenceWorkspace({ raceBook, field, formGuide, raceKey, clean }: RaceIntelligenceWorkspaceProps) {
  const [intelligenceRace, setIntelligenceRace] = useState<CurrentRaceIntelligenceRace | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "loaded" | "unavailable">("loading");

  useEffect(() => {
    let cancelled = false;
    setLoadState("loading");
    loadCurrentRaceIntelligenceFeed()
      .then((payload) => {
        if (cancelled) return;
        setIntelligenceRace(findCurrentRaceIntelligenceRace(payload, raceKey));
        setLoadState("loaded");
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn("Current race intelligence feed unavailable", error);
          setIntelligenceRace(null);
          setLoadState("unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey]);

  const model = useMemo(
    () => buildRaceIntelligenceViewModel({ raceBook, field, formGuide, intelligenceRace }),
    [raceBook, field, formGuide, intelligenceRace],
  );

  return (
    <section className="eiq-race-intel-v1">
      <div className="eiq-epi-v1-hero">
        <div>
          <p>RACE</p>
          <h3>{clean(raceBook?.official?.meeting)} R{clean(raceBook?.official?.raceNumber)}</h3>
          <span>Race intelligence, governed runner board and current-race context.</span>
        </div>
        <dl>
          <div><dt>Feed</dt><dd>{loadState === "loaded" && intelligenceRace ? "Current" : loadState === "loading" ? "Loading" : "Unavailable"}</dd></div>
          <div><dt>Runners</dt><dd>{model.runnerBoard.length}</dd></div>
        </dl>
      </div>

      <div className="eiq-race-intel-card-grid">
        {model.cards.map((card) => (
          <article key={card.label} className="eiq-epi-v1-panel eiq-race-intel-card">
            <span>{card.label}</span>
            <strong>{display(card.value)}</strong>
            <p>{card.detail}</p>
          </article>
        ))}
      </div>

      <div className="eiq-race-intel-main-grid">
        <section className="eiq-epi-v1-panel">
          <div className="eiq-epi-v1-panel__title"><span>What Matters Today</span></div>
          {model.whatMatters.length ? (
            <ul className="eiq-race-intel-list">
              {model.whatMatters.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : (
            <p className="eiq-epi-v1-copy">Governed race statements are not available for this race.</p>
          )}
        </section>

        <section className="eiq-epi-v1-panel">
          <div className="eiq-epi-v1-panel__title"><span>Speed Map Preview</span></div>
          {model.speedMap.length ? (
            <div className="eiq-race-intel-map-preview">
              {model.speedMap.map((lane) => (
                <div key={lane.zone}>
                  <strong>{lane.zone}</strong>
                  <p>{lane.runners.slice(0, 4).join(" | ")}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="eiq-epi-v1-copy">Projected map feed is unresolved for this race.</p>
          )}
        </section>

        <section className="eiq-epi-v1-panel">
          <div className="eiq-epi-v1-panel__title"><span>EPI Top 3</span></div>
          {model.topEpi.length ? (
            <ol className="eiq-race-intel-top3">
              {model.topEpi.map((item) => <li key={`${item.no}-${item.runner}`}><span>{item.no}</span><strong>{item.runner}</strong><em>{item.value}</em></li>)}
            </ol>
          ) : (
            <p className="eiq-epi-v1-copy">Top EPI snapshot is not available for this race.</p>
          )}
        </section>
      </div>

      {model.unavailable.length ? (
        <section className="eiq-race-intel-unavailable" aria-label="Unavailable governed fields">
          {model.unavailable.map((item) => <span key={item}>{item}</span>)}
        </section>
      ) : null}

      <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
        <div className="eiq-epi-v1-panel__title"><span>Runner Board</span></div>
        <div className="eiq-epi-v1-table-scroll">
          <table className="eiq-epi-v1-table eiq-race-intel-runner-board">
            <thead>
              <tr>
                <th>NO</th>
                <th>SILK</th>
                <th>RUNNER</th>
                <th>BAR</th>
                <th>WGT</th>
                <th>JOCKEY</th>
                <th>TRAINER</th>
                <th>EPI SPD</th>
                <th>EDGEiQ</th>
                <th>MARKET</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {model.runnerBoard.map((row) => (
                <tr key={`${row.no}-${row.runner}`} className={row.status.toLowerCase().includes("scratch") ? "is-unavailable" : ""}>
                  <td>{row.no}</td>
                  <td><Silk src={row.silkUrl} runner={row.runner} /></td>
                  <td><strong>{row.runner}</strong></td>
                  <td>{display(row.barrier)}</td>
                  <td>{display(row.weight)}</td>
                  <td>{display(row.jockey)}</td>
                  <td>{display(row.trainer)}</td>
                  <td>{display(row.epiSpeed)}</td>
                  <td>{display(row.edgeiq)}</td>
                  <td>{display(row.market)}</td>
                  <td>{display(row.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
'''


FIELD_WORKSPACE = r'''import { useMemo, useState } from "react";
import { buildFieldWorkspaceRows } from "../services/fieldWorkspaceViewModel";
import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";

type FieldWorkspaceProps = {
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  onOpenRunner: (index: number) => void;
};

export function FieldWorkspace({ field, formGuide, clean, weight, market, onOpenRunner }: FieldWorkspaceProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const rows = useMemo(() => buildFieldWorkspaceRows({ field, formGuide, weight, market }), [field, formGuide, weight, market]);

  return (
    <section className="eiq-workspace-panel eiq-field-workspace-v1">
      <div className="eiq-workspace-panel__title">
        <span>FIELD</span>
        <strong>Race field</strong>
        <p>Official runners with governed EDGEiQ fields where available.</p>
      </div>

      <div className="eiq-table-wrap">
        <table className="eiq-field-table-v1">
          <thead>
            <tr>
              <th>NO</th>
              <th>SILK</th>
              <th className="is-left">RUNNER</th>
              <th>BAR</th>
              <th>WGT</th>
              <th className="is-left">JOCKEY</th>
              <th className="is-left">TRAINER</th>
              <th>EDGEiQ</th>
              <th>MARKET</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((runner) => {
              const expanded = expandedKey === runner.key;
              return (
                <>
                  <tr
                    key={runner.key}
                    className={runner.status.toLowerCase().includes("scratch") ? "is-scratched" : ""}
                  >
                    <td>{runner.no}</td>
                    <td>
                      {runner.silkUrl && runner.silkUrl.startsWith("http") ? (
                        <img className="eiq-field-table-v1__silk" src={runner.silkUrl} alt="" loading="lazy" />
                      ) : (
                        <span className="eiq-field-table-v1__silk eiq-race-intel-silk--empty" aria-hidden="true" />
                      )}
                    </td>
                    <td className="is-left">
                      <button
                        type="button"
                        className="eiq-field-runner-button"
                        onClick={() => setExpandedKey(expanded ? null : runner.key)}
                      >
                        <strong>{runner.runner}</strong>
                      </button>
                    </td>
                    <td>{runner.barrier || "-"}</td>
                    <td>{runner.weight || "-"}</td>
                    <td className="is-left">{runner.jockey || "-"}</td>
                    <td className="is-left">{runner.trainer || "-"}</td>
                    <td>{runner.edgeiq || "-"}</td>
                    <td>{runner.market || "-"}</td>
                    <td>{runner.status || "-"}</td>
                  </tr>
                  {expanded ? (
                    <tr key={`${runner.key}-recent`} className="eiq-field-expanded-row">
                      <td colSpan={10}>
                        <div className="eiq-field-recent-panel">
                          <div>
                            <span>LAST FIVE STARTS</span>
                            <button type="button" onClick={() => onOpenRunner(runner.sourceIndex)}>Open runner profile</button>
                          </div>
                          {runner.recentRuns.length ? (
                            <table>
                              <thead>
                                <tr>
                                  <th>Date</th>
                                  <th>Track</th>
                                  <th>Dist</th>
                                  <th>Class</th>
                                  <th>Going</th>
                                  <th>Pos</th>
                                  <th>Margin</th>
                                  <th>SP</th>
                                  <th>EPI</th>
                                </tr>
                              </thead>
                              <tbody>
                                {runner.recentRuns.map((run, index) => (
                                  <tr key={`${runner.key}-run-${index}`}>
                                    <td>{run.date || "-"}</td>
                                    <td>{run.track || "-"}</td>
                                    <td>{run.distance || "-"}</td>
                                    <td>{run.raceClass || "-"}</td>
                                    <td>{run.condition || "-"}</td>
                                    <td>{run.position || "-"}</td>
                                    <td>{run.margin || "-"}</td>
                                    <td>{run.sp || "-"}</td>
                                    <td>{run.epi || "-"}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <p>Governed recent-start rows are not available for this runner.</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
'''


PERFORMANCE_WORKSPACE = r'''import { useEffect, useMemo, useState } from "react";
import {
  buildEpiWorkspaceViewModel,
  loadEpiWorkspaceTerminalFeed,
} from "../services/epiWorkspaceFeed";
import {
  buildPerformanceIntelligenceService,
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceRaceContext,
} from "../../services/performance-intelligence";
import {
  buildPerformanceWorkspaceViewModel,
  type PerformanceHeatCell,
} from "../services/performanceWorkspaceViewModel";

type PerformanceWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
};

function value(text: string | null | undefined): string {
  return text && text.trim() ? text : "";
}

function statusClass(valueText: string): string {
  const text = valueText.toLowerCase();
  if (text.includes("no governed") || text.includes("not")) return "is-pending";
  return "is-current";
}

function DetailPanel({ cell }: { cell: PerformanceHeatCell | null }) {
  const entries = Object.entries(cell?.context ?? {}).filter(([, detail]) => detail);
  return (
    <aside className="eiq-epi-v1-side">
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Run Detail</span></div>
        {cell && entries.length ? (
          <dl className="eiq-epi-v1-context">
            {entries.map(([label, detail]) => (
              <div key={label}><dt>{label}</dt><dd>{detail}</dd></div>
            ))}
          </dl>
        ) : (
          <p className="eiq-epi-v1-copy">Select a populated historical cell to inspect available run detail.</p>
        )}
      </section>
    </aside>
  );
}

export function PerformanceWorkspace({ raceKey, meetingKey = null, raceLabel = null }: PerformanceWorkspaceProps) {
  const [epiRows, setEpiRows] = useState<Awaited<ReturnType<typeof loadEpiWorkspaceTerminalFeed>>>([]);
  const [performanceContext, setPerformanceContext] = useState<PerformanceIntelligenceRaceContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<PerformanceHeatCell | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([loadEpiWorkspaceTerminalFeed(), loadPerformanceIntelligenceFeed()])
      .then(([terminalRows, feed]) => {
        if (cancelled) return;
        setEpiRows(terminalRows);
        setPerformanceContext(buildPerformanceIntelligenceService(feed).getRaceContext(raceKey));
        setError(null);
      })
      .catch((loadError) => {
        if (!cancelled) {
          setEpiRows([]);
          setPerformanceContext(null);
          setError(loadError instanceof Error ? loadError.message : "Performance workspace feed failed");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey]);

  useEffect(() => {
    setSelectedCell(null);
  }, [raceKey]);

  const epiViewModel = useMemo(() => buildEpiWorkspaceViewModel(raceKey, epiRows, meetingKey), [raceKey, epiRows, meetingKey]);
  const viewModel = useMemo(() => buildPerformanceWorkspaceViewModel(epiViewModel.rows, performanceContext), [epiViewModel.rows, performanceContext]);

  if (loading) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Loading governed performance history.</div></section>;
  }

  if (error) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">{error}</div></section>;
  }

  if (!viewModel.rows.length) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Governed historical performance rows are not available for this race.</div></section>;
  }

  return (
    <section className="eiq-epi-v1 eiq-performance-v2">
      <div className="eiq-epi-v1-hero">
        <div>
          <p>PERFORMANCE</p>
          <h3>{raceLabel || "Historical Performance"}</h3>
          <span>Historical performance heat map with available run context.</span>
        </div>
        <dl>
          <div><dt>Status</dt><dd className={statusClass(viewModel.sourceSummary)}>{viewModel.sourceSummary}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Historical Runs</dt><dd>{viewModel.historicalRuns}</dd></div>
        </dl>
      </div>

      <section className="eiq-epi-v1-summary">
        <div>
          <span>Race Benchmark</span>
          <strong>{raceLabel || "Selected Race"}</strong>
        </div>
        <dl>
          {viewModel.raceBenchmark.map((item) => (
            <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>
          ))}
        </dl>
      </section>

      <div className="eiq-epi-v1-grid">
        <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
          <div className="eiq-epi-v1-panel__title">
            <span>Performance Heat Map</span>
            <small>Historical rating cells only; empty cells remain unavailable.</small>
          </div>
          <div className="eiq-epi-v1-table-scroll">
            <table className="eiq-epi-v1-table eiq-performance-v2-table">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Runner</th>
                  <th>Current</th>
                  <th>Peak</th>
                  <th>Average</th>
                  <th>Runs</th>
                  <th>L5</th>
                  <th>L4</th>
                  <th>L3</th>
                  <th>L2</th>
                  <th>L1</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.rows.map((row) => (
                  <tr key={row.key}>
                    <td>{row.no}</td>
                    <td><strong>{row.runner}</strong></td>
                    <td>{value(row.current) || "-"}</td>
                    <td>{value(row.peak) || "-"}</td>
                    <td>{value(row.average) || "-"}</td>
                    <td>{row.validStarts}</td>
                    {Array.from({ length: 5 }).map((_, index) => {
                      const cell = row.cells[index];
                      return (
                        <td key={`${row.key}-cell-${index}`}>
                          {cell?.value ? (
                            <button
                              type="button"
                              className={`eiq-epi-v1-tile is-${cell.tileClass}${selectedCell === cell ? " is-selected" : ""}`}
                              title={Object.entries(cell.context).filter(([, detail]) => detail).map(([label, detail]) => `${label}: ${detail}`).join("\n")}
                              onClick={() => setSelectedCell(cell)}
                            >
                              {cell.value}
                            </button>
                          ) : (
                            <span className="eiq-epi-v1-tile is-missing">-</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="eiq-epi-v1-legend" aria-label="Performance heat map legend">
            <span><i className="is-positive" /> Strong</span>
            <span><i className="is-neutral" /> Around benchmark</span>
            <span><i className="is-negative" /> Below benchmark</span>
            <span><i className="is-missing" /> Not supplied</span>
          </div>
        </section>
        <DetailPanel cell={selectedCell} />
      </div>
    </section>
  );
}
'''


CSS_BLOCK = r'''
/* EDGEIQ RACE/FIELD/PERFORMANCE/EPI tranche V1 */
.eiq-race-intel-v1,
.eiq-performance-v2 {
  display: grid;
  gap: 16px;
}

.eiq-race-intel-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.eiq-race-intel-card {
  min-height: 112px;
}

.eiq-race-intel-card strong {
  display: block;
  margin: 8px 0 6px;
  font-size: 1.25rem;
}

.eiq-race-intel-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.25fr) minmax(280px, .8fr);
  gap: 12px;
}

.eiq-race-intel-list {
  margin: 0;
  padding-left: 18px;
  color: var(--edgeiq-text-primary);
}

.eiq-race-intel-list li + li {
  margin-top: 8px;
}

.eiq-race-intel-map-preview {
  display: grid;
  gap: 8px;
}

.eiq-race-intel-map-preview > div {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-race-intel-map-preview > div:last-child {
  border-bottom: 0;
}

.eiq-race-intel-top3 {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.eiq-race-intel-top3 li {
  display: grid;
  grid-template-columns: 36px 1fr auto;
  gap: 8px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-race-intel-top3 li:last-child {
  border-bottom: 0;
}

.eiq-race-intel-top3 em {
  font-style: normal;
  color: var(--edgeiq-primary);
  font-weight: 800;
}

.eiq-race-intel-unavailable {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.eiq-race-intel-unavailable span {
  padding: 6px 10px;
  border: 1px solid var(--edgeiq-border);
  border-radius: 999px;
  background: #ffffff;
  color: var(--edgeiq-text-secondary);
  font-size: .78rem;
}

.eiq-race-intel-silk,
.eiq-field-table-v1__silk {
  width: 34px;
  height: 34px;
  object-fit: contain;
  border-radius: 6px;
}

.eiq-race-intel-silk--empty {
  display: inline-block;
  border: 1px solid var(--edgeiq-border);
  background: #f8fafc;
}

.eiq-race-intel-runner-board th:nth-child(3),
.eiq-race-intel-runner-board td:nth-child(3),
.eiq-performance-v2-table th:nth-child(2),
.eiq-performance-v2-table td:nth-child(2) {
  text-align: left;
}

.eiq-field-runner-button {
  border: 0 !important;
  background: transparent !important;
  padding: 0 !important;
  color: var(--edgeiq-text-primary) !important;
  cursor: pointer;
}

.eiq-field-runner-button:hover strong {
  color: var(--edgeiq-primary);
}

.eiq-field-expanded-row > td {
  background: #f8fafc !important;
}

.eiq-field-recent-panel {
  display: grid;
  gap: 10px;
}

.eiq-field-recent-panel > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.eiq-field-recent-panel table {
  width: 100%;
  border-collapse: collapse;
  font-size: .82rem;
}

.eiq-field-recent-panel th,
.eiq-field-recent-panel td {
  padding: 7px 8px;
  border-bottom: 1px solid var(--edgeiq-border-soft);
  text-align: left;
}

.eiq-field-recent-panel button {
  border: 1px solid var(--edgeiq-border) !important;
  border-radius: 8px;
  background: #ffffff !important;
  color: var(--edgeiq-primary) !important;
  padding: 6px 10px;
  font-size: .78rem;
  font-weight: 800;
  text-transform: uppercase;
}

@media (max-width: 1100px) {
  .eiq-race-intel-card-grid,
  .eiq-race-intel-main-grid {
    grid-template-columns: 1fr;
  }
}
'''


AUDIT_SCRIPT = r'''from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "full-product-implementation"
PUBLIC = ROOT / "public" / "data"

FILES = [
    ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "PerformanceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "EpiWorkspaceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css",
]

def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["check", "status", "detail"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

source = "\n".join(text(path) for path in FILES)

checks = [
    {
        "check": "RACE route maps to RACE workspace tab",
        "status": "PASS" if 'race: "RACE"' in text(ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx") else "FAIL",
        "detail": "RaceFileV3 global route mapping",
    },
    {
        "check": "Approved race runner board labels present",
        "status": "PASS" if all(label in source for label in ["EPI SPD", "EDGEiQ", "Runner Board", "What Matters Today"]) else "FAIL",
        "detail": "RACE workspace labels",
    },
    {
        "check": "Approved field labels present",
        "status": "PASS" if all(label in text(ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx") for label in ["EDGEiQ", "LAST FIVE STARTS", "STATUS"]) else "FAIL",
        "detail": "FIELD workspace labels",
    },
    {
        "check": "Performance and EPI components differ",
        "status": "PASS" if "Performance Heat Map" in source and "EPI Matrix" in source else "FAIL",
        "detail": "PERFORMANCE is not an EPI ranking clone",
    },
    {
        "check": "No visible Confidence label in tranche workspaces",
        "status": "PASS" if not re.search(r">\s*Confidence\s*<|[\"']Confidence[\"']", source) else "FAIL",
        "detail": "Visible label scan",
    },
    {
        "check": "No product-facing demo/mock/sample runner rows",
        "status": "PASS" if not re.search(r"demo runner|sample runner|mock runner|synthetic runner", source, re.I) else "FAIL",
        "detail": "Mock data language scan",
    },
    {
        "check": "No coloured saddlecloth number background classes added",
        "status": "PASS" if "saddlecloth-number" not in source and "runner-number-badge" not in source else "FAIL",
        "detail": "Saddlecloth style scan",
    },
]

write_csv(PUBLIC / "edgeiq_workspace_route_audit_v1.csv", checks[:1])
write_csv(PUBLIC / "edgeiq_mock_data_audit_v1.csv", [checks[5]])
write_csv(PUBLIC / "edgeiq_saddlecloth_style_audit_v1.csv", [checks[6]])
write_csv(PUBLIC / "edgeiq_governed_metric_audit_v1.csv", checks[1:4])
write_csv(PUBLIC / "edgeiq_ui_language_audit_v1.csv", [checks[4]])
write_csv(DOC / "edgeiq_race_field_performance_epi_audit_v1.csv", checks)

md = ["# EDGEIQ Race/Field/Performance/EPI Audit V1", ""]
for row in checks:
    md.append(f"- {row['status']}: {row['check']} - {row['detail']}")
(DOC / "EDGEIQ_RACE_FIELD_PERFORMANCE_EPI_AUDIT_V1.md").write_text("\n".join(md) + "\n", encoding="utf-8")

failed = [row for row in checks if row["status"] != "PASS"]
if failed:
    for row in failed:
        print(f"FAIL: {row['check']} :: {row['detail']}")
    raise SystemExit(1)

print("EDGEIQ_RACE_FIELD_PERFORMANCE_EPI_AUDIT_PASS")
'''


def main() -> None:
    files_to_checkpoint = [
        ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx",
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx",
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx",
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "PerformanceWorkspace.tsx",
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "EpiWorkspaceWorkspace.tsx",
        ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css",
    ]
    for path in files_to_checkpoint:
        checkpoint(path)

    write_trace()

    write(ROOT / "src" / "edgeiq-os" / "race" / "services" / "currentRaceIntelligenceFeed.ts", CURRENT_RACE_INTELLIGENCE_FEED)
    write(ROOT / "src" / "edgeiq-os" / "race" / "services" / "raceWorkspaceViewModel.ts", RACE_WORKSPACE_VIEW_MODEL)
    write(ROOT / "src" / "edgeiq-os" / "race" / "services" / "fieldWorkspaceViewModel.ts", FIELD_WORKSPACE_VIEW_MODEL)
    write(ROOT / "src" / "edgeiq-os" / "race" / "services" / "performanceWorkspaceViewModel.ts", PERFORMANCE_WORKSPACE_VIEW_MODEL)
    write(ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx", RACE_INTELLIGENCE_WORKSPACE)
    write(ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx", FIELD_WORKSPACE)
    write(ROOT / "src" / "edgeiq-os" / "race" / "components" / "PerformanceWorkspace.tsx", PERFORMANCE_WORKSPACE)
    write(ROOT / "scripts" / "audit_edgeiq_race_field_performance_epi_v1.py", AUDIT_SCRIPT)

    race_workspace = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
    text = read(race_workspace)
    if 'import { RaceIntelligenceWorkspace } from "./RaceIntelligenceWorkspace";' not in text:
        text = text.replace('import { FieldWorkspace } from "./FieldWorkspace";', 'import { FieldWorkspace } from "./FieldWorkspace";\nimport { RaceIntelligenceWorkspace } from "./RaceIntelligenceWorkspace";')
    text = text.replace('const tabs = ["FIELD", "FORM GUIDE", "PERFORMANCE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "REVIEW"] as const;', 'const tabs = ["RACE", "FIELD", "FORM GUIDE", "PERFORMANCE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "REVIEW"] as const;')
    text = text.replace(
        '''      {tab === "FIELD" ? (
        <FieldWorkspace
          field={field}
          clean={clean}
          weight={weight}
          market={market}
          onOpenRunner={onOpenRunner}
        />
      ) : tab === "FORM GUIDE" ? (''',
        '''      {tab === "RACE" ? (
        <RaceIntelligenceWorkspace
          raceBook={raceBook}
          field={field}
          formGuide={formGuide}
          raceKey={clean(official.raceKey) || selectedRaceKey}
          clean={clean}
        />
      ) : tab === "FIELD" ? (
        <FieldWorkspace
          field={field}
          formGuide={formGuide}
          clean={clean}
          weight={weight}
          market={market}
          onOpenRunner={onOpenRunner}
        />
      ) : tab === "FORM GUIDE" ? (''',
    )
    write(race_workspace, text)

    race_file = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
    replace_once(race_file, '  race: "OVERVIEW",', '  race: "RACE",')

    append_once(ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css", "EDGEIQ RACE/FIELD/PERFORMANCE/EPI tranche V1", CSS_BLOCK)

    print(f"Created checkpoints in {CHECKPOINT_DIR}")
    print("Applied EDGEIQ race/field/performance/EPI tranche V1")


if __name__ == "__main__":
    main()
