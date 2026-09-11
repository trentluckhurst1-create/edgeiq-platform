import type { FormGuideRaceDisplay, FormGuideRecentRun, FormGuideRunnerDisplay } from "./formGuideNormaliser";

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
  gear: string;
  edgeiq: string;
  market: string;
  status: string;
  isScratched: boolean;
  recentRuns: FormGuideRecentRun[];
};

function clean(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || /^(none|null|undefined|nan|not available|unavailable)$/i.test(text)) return "";
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
  const raw = clean(firstValue(row, ["status", "official.status", "scratchingStatus", "official.scratchingStatus", "availability"]));
  if (raw) return raw;
  const scratched = firstValue(row, ["scratched", "official.scratched", "isScratched", "is_scratch", "is_scratched"]);
  return scratched === true || String(scratched).toUpperCase() === "TRUE" ? "Scratched" : "Active";
}

function normaliseStatus(status: string, marketValue: string): { status: string; isScratched: boolean } {
  const statusScratched = /scratch/i.test(status);
  const marketScratched = /^scratched$/i.test(clean(marketValue));
  const isScratched = statusScratched || marketScratched;
  return { status: isScratched ? "Scratched" : clean(status) || "Active", isScratched };
}

export function buildFieldWorkspaceRows(params: {
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  weight: (value: any) => string;
  market: (value: any) => string;
}): FieldWorkspaceRow[] {
  const rows = Array.isArray(params.field) ? params.field : [];
  return rows.map((runner, index) => {
    const no = clean(firstValue(runner, ["official.number", "number", "runnerNumber", "runner_number", "saddlecloth", "no"])) || String(index + 1);
    const runnerName = clean(firstValue(runner, ["official.runner", "runner", "runnerName", "runner_name", "horse", "horseName", "name"]));
    const formRunner = matchFormRunner(params.formGuide, no, runnerName);
    const rawStatus = statusForRunner(runner, formRunner);
    const rawMarket = clean(formRunner?.marketPrice) || clean(params.market(firstValue(runner, ["official.market", "market", "live", "price", "marketPrice", "market_price", "tabPrice", "fixedOdds"]))) || "";
    const { status, isScratched } = normaliseStatus(rawStatus, rawMarket);
    const edgeiq = clean(formRunner?.epi) || clean(firstValue(runner, ["metrics.epi", "epi", "currentEpi", "current_epi", "horsePerformanceRating", "performanceRating", "rating", "official.epi"]));
    const weightValue = clean(formRunner?.weight) || clean(params.weight(firstValue(runner, [
      "official.weight",
      "official.allocatedWeight",
      "official.handicapWeight",
      "official.weightCarried",
      "weight",
      "allocated_weight",
      "allocatedWeight",
      "handicap_weight",
      "handicapWeight",
      "weight_carried",
      "weightCarried",
      "runner_weight",
      "runnerWeight",
      "weight_kg",
      "weightKg",
      "wt",
    ])));
    const gear = clean(firstValue(runner, [
      "official.gearChanges",
      "official.gear",
      "gearChanges",
      "gear_changes",
      "gear",
      "equipment",
    ]));

    return {
      key: `${no}-${runnerName || formRunner?.horse || index}`,
      sourceIndex: index,
      no,
      silkUrl: formRunner?.silkUrl || clean(firstValue(runner, ["official.silkUrl", "silkUrl", "silksUrl", "silk"])),
      runner: formRunner?.horse || runnerName,
      barrier: formRunner?.barrier || clean(firstValue(runner, ["official.barrier", "barrier", "bar", "draw"])),
      weight: weightValue,
      jockey: formRunner?.jockey || clean(firstValue(runner, ["official.jockey", "jockey", "jockeyName", "jockey_name"])),
      trainer: formRunner?.trainer || clean(firstValue(runner, ["official.trainer", "trainer", "trainerName", "trainer_name"])),
      gear,
      edgeiq: isScratched ? "" : edgeiq,
      market: isScratched ? "Scratched" : rawMarket,
      status,
      isScratched,
      recentRuns: (formRunner?.recentRuns ?? []).slice(0, 5),
    };
  });
}
