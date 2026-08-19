import type { FormGuideRaceDisplay, FormGuideRunnerDisplay } from "./formGuideNormaliser";
import type { CurrentRaceIntelligenceRace, CurrentRaceIntelligenceRunner } from "./currentRaceIntelligenceFeed";

export type RaceRunnerBoardRow = {
  no: string;
  silkUrl: string;
  runner: string;
  barrier: string;
  weight: string;
  jockey: string;
  trainer: string;
  epi: string;
  earlySpeed: string;
  edgeiqPrice: string;
  market: string;
  status: string;
  scratched: boolean;
  evidenceStatus: string;
};

export type RaceIntelligenceCard = { label: string; value: string; detail: string };

export type RaceIntelligenceViewModel = {
  cards: RaceIntelligenceCard[];
  whatMatters: string[];
  speedMap: Array<{ zone: string; runners: Array<{ no: string; runner: string; earlySpeed: string }> }>;
  topEpi: Array<{ no: string; runner: string; value: string; status: string }>;
  runnerBoard: RaceRunnerBoardRow[];
  marketSnapshot: Array<{ label: string; value: string }>;
  unavailable: string[];
};

function clean(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).replace(/\s+/g, " ").trim();
  if (!text || text === "-" || text === "--") return "";
  if (["none", "null", "undefined", "nan", "n/a", "na", "unavailable"].includes(text.toLowerCase())) return "";
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
  return Number.isFinite(number) && number > 0 ? `$${number.toFixed(2)}` : "";
}

function numberText(value: unknown, decimals = 1): string {
  const text = clean(value);
  if (!text) return "";
  const number = Number(text);
  return Number.isFinite(number) ? number.toFixed(decimals) : text;
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

function boardEvidenceStatus(intelligence: CurrentRaceIntelligenceRunner | null, epiValue: string): string {
  const status = clean(intelligence?.epi?.status);
  if (status) return status.replace(/_/g, " ");
  return epiValue ? "Available" : "Insufficient Evidence";
}

function rowFromFormRunner(runner: FormGuideRunnerDisplay, intelligence: CurrentRaceIntelligenceRunner | null): RaceRunnerBoardRow {
  const scratched = Boolean(runner.scratched || intelligence?.scratched);
  const epi = numberText(intelligence?.epi?.display ?? intelligence?.epi?.value) || runner.epi;
  return {
    no: runner.no,
    silkUrl: runner.silkUrl,
    runner: runner.horse,
    barrier: runner.barrier,
    weight: runner.weight,
    jockey: runner.jockey,
    trainer: runner.trainer,
    epi,
    earlySpeed: numberText(intelligence?.earlySpeed?.value, 0) || runner.earlySpeed,
    edgeiqPrice: scratched ? "" : price(intelligence?.edgeiqPrice?.value) || runner.edgeiqPrice,
    market: scratched ? "" : price(intelligence?.market?.value) || runner.marketPrice,
    status: scratched ? "Scratched" : "Active",
    scratched,
    evidenceStatus: scratched ? "Scratched" : boardEvidenceStatus(intelligence, epi),
  };
}

function rowFromRawRunner(row: any, index: number, race: CurrentRaceIntelligenceRace | null): RaceRunnerBoardRow {
  const no = clean(firstValue(row, ["official.number", "number", "runnerNumber", "saddlecloth", "no"])) || String(index + 1);
  const runner = clean(firstValue(row, ["official.runner", "runner", "runnerName", "horse", "name"]));
  const intelligence = intelligenceRunnerFor(race, no, runner);
  const scratched = Boolean(intelligence?.scratched);
  const epi = numberText(intelligence?.epi?.display ?? intelligence?.epi?.value);
  return {
    no,
    silkUrl: clean(firstValue(row, ["official.silkUrl", "silkUrl", "silksUrl", "silk"])),
    runner,
    barrier: clean(firstValue(row, ["official.barrier", "barrier", "bar", "draw"])),
    weight: clean(firstValue(row, ["official.weight", "weight", "wt"])),
    jockey: clean(firstValue(row, ["official.jockey", "jockey"])),
    trainer: clean(firstValue(row, ["official.trainer", "trainer"])),
    epi,
    earlySpeed: numberText(intelligence?.earlySpeed?.value, 0),
    edgeiqPrice: scratched ? "" : price(intelligence?.edgeiqPrice?.value),
    market: scratched ? "" : price(intelligence?.market?.value),
    status: scratched ? "Scratched" : "Active",
    scratched,
    evidenceStatus: scratched ? "Scratched" : boardEvidenceStatus(intelligence, epi),
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
    status: "Available",
  })).filter((item) => item.runner && item.value) ?? [];
  if (supplied.length) return supplied.slice(0, 3);
  return board
    .filter((row) => !row.scratched)
    .map((row) => ({ row, value: Number(row.epi.replace(/[$,]/g, "")) }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, 3)
    .map((item) => ({ no: item.row.no, runner: item.row.runner, value: item.row.epi, status: item.row.evidenceStatus }));
}

function speedMapFromRace(race: CurrentRaceIntelligenceRace | null): RaceIntelligenceViewModel["speedMap"] {
  const lanes = ["LEAD", "ON PACE", "MIDFIELD", "BACK", "UNRESOLVED"];
  const grouped = new Map<string, Array<{ no: string; runner: string; earlySpeed: string }>>();
  lanes.forEach((lane) => grouped.set(lane, []));
  (race?.runners ?? []).forEach((runner) => {
    if (runner.scratched) return;
    const zone = clean(runner.projectedMapZone).replace(/_/g, " ").toUpperCase() || "UNRESOLVED";
    const lane = lanes.includes(zone) ? zone : zone.includes("LEAD") ? "LEAD" : zone.includes("PACE") ? "ON PACE" : zone.includes("BACK") ? "BACK" : zone.includes("MID") ? "MIDFIELD" : "UNRESOLVED";
    const name = clean(runner.runnerName);
    if (name) grouped.get(lane)?.push({ no: clean(runner.runnerNumber), runner: name, earlySpeed: numberText(runner.earlySpeed?.value, 0) });
  });
  return lanes.map((zone) => ({ zone, runners: grouped.get(zone) ?? [] })).filter((item) => item.runners.length || item.zone !== "UNRESOLVED");
}

function conciseStatement(value: string): string {
  const text = clean(value).replace(/\.$/, "");
  return text.length > 90 ? `${text.slice(0, 87).trim()}...` : text;
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
    .map((item) => conciseStatement(clean(item.statement)))
    .filter(Boolean)
    .slice(0, 5);
  const unavailable: string[] = [];
  const tempo = clean(intelligenceRace?.tempo ?? intelligenceRace?.pressure ?? firstValue(official, ["tempo", "raceTempo"]));
  const epf = clean(firstValue(official, ["epf", "edgeiqPerformanceFigure"])) || (intelligenceRace?.fieldSummary?.epi?.average ? numberText(intelligenceRace.fieldSummary.epi.average) : "");
  const mapCoverage = intelligenceRace?.mapCoverage?.count ?? intelligenceRace?.fieldSummary?.earlySpeed?.count ?? 0;
  const hiddenAngles = statements.length ? `${statements.length} supplied` : "Insufficient Evidence";
  const determinant = statements[0] || topEpi[0]?.runner || "Insufficient Evidence";
  if (!tempo) unavailable.push("Awaiting Map Evidence");
  if (!epf) unavailable.push("Insufficient Performance Evidence");
  if (!statements.length) unavailable.push("Insufficient Governed Statements");
  return {
    cards: [
      { label: "TEMPO", value: tempo || "Awaiting Map Evidence", detail: mapCoverage ? `${mapCoverage} runners mapped` : "Governed map evidence pending" },
      { label: "EPF", value: epf || "Insufficient Evidence", detail: "Expected performance figure" },
      { label: "KEY DETERMINANTS", value: determinant, detail: statements.length ? "Governed race intelligence" : "No determinant supplied" },
      { label: "HIDDEN ANGLES", value: hiddenAngles, detail: statements[1] || "No hidden angle supplied" },
    ],
    whatMatters: statements.length ? statements : unavailable.slice(0, 3),
    speedMap: speedMapFromRace(intelligenceRace ?? null),
    topEpi,
    runnerBoard: board,
    marketSnapshot: [
      { label: "Favourite", value: board.find((row) => row.market)?.runner || "Awaiting Market" },
      { label: "Best EPI", value: topEpi[0]?.runner || "Insufficient Evidence" },
      { label: "Market", value: board.some((row) => row.market) ? "Market Available" : "Awaiting Market" },
    ],
    unavailable,
  };
}
