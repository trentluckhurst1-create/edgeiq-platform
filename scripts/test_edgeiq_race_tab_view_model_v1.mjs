import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import ts from "typescript";

const repoRoot = process.cwd();
const sourcePath = path.join(repoRoot, "src", "edgeiq-os", "race", "services", "raceWorkspaceViewModel.ts");
const source = await readFile(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ES2022,
    importsNotUsedAsValues: ts.ImportsNotUsedAsValues.Remove,
  },
  fileName: sourcePath,
}).outputText;

const tmp = await mkdtemp(path.join(os.tmpdir(), "edgeiq-race-view-model-"));
const compiledPath = path.join(tmp, "raceWorkspaceViewModel.mjs");
await writeFile(compiledPath, compiled, "utf8");
const { buildRaceIntelligenceViewModel, raceWorkspaceViewModelTestExports } = await import(`file:///${compiledPath.replace(/\\/g, "/")}`);

function runner(overrides) {
  return {
    id: `runner-${overrides.no}`,
    sourceIndex: Number(overrides.no) - 1,
    no: String(overrides.no),
    sortNo: Number(overrides.no),
    silkUrl: "",
    lastFive: [],
    horse: overrides.runner,
    age: "",
    sex: "",
    breeding: "",
    trainer: overrides.trainer ?? "Trainer",
    jockey: overrides.jockey ?? "Jockey",
    weight: overrides.weight ?? "57kg",
    barrier: overrides.barrier ?? String(overrides.no),
    effectiveBarrier: "",
    daysSinceLastRun: "",
    rating: "",
    epi: overrides.epr ?? "",
    epiRank: "",
    epiFieldAverage: "",
    epiDifference: "",
    earlySpeed: overrides.speed ?? "",
    earlySpeedLabel: "Early Speed",
    marketPrice: overrides.market ?? "",
    edgeiqPrice: overrides.edgeiqPrice ?? "",
    suitabilityScore: "",
    suitabilityLabel: "",
    shapeFit: "",
    late: "",
    formMomentum: "",
    formMomentumDirection: "",
    scratched: Boolean(overrides.scratched),
    country: "",
    gear: "",
    careerProfile: [],
    conditionProfile: [],
    classProfile: [],
    jockeyProfile: [],
    raceDayPattern: [],
    lastStart: null,
    insights: overrides.insight
      ? [{ key: "governed", title: "Governed", items: [{ text: overrides.insight, tone: "NEUTRAL", source: "fixture" }] }]
      : [],
    governedStatements: overrides.insight ? [overrides.insight] : [],
    recentRuns: [],
  };
}

const formGuide = {
  meeting: "Sandown Hillside",
  date: "2026-08-22",
  raceNumber: "1",
  raceName: "Race 1",
  primaryLine: "",
  metadata: [],
  activeFieldEpi: { validRunnerCount: 0, fieldAverage: null },
  fieldSummary: "",
  runners: [
    runner({ no: 1, runner: "Scratch High", epr: "99.0", speed: "70", edgeiqPrice: "$2.00", market: "$3.00", scratched: true }),
    runner({ no: 2, runner: "Alpha", epr: "50.0", speed: "62", edgeiqPrice: "$4.20", market: "$5.00", insight: "Early speed projects into the forward group." }),
    runner({ no: 3, runner: "Bravo", epr: "50.0", speed: "61", edgeiqPrice: "$4.40", market: "$6.00" }),
    runner({ no: 4, runner: "Missing EPR", epr: "", speed: "", edgeiqPrice: "", market: "$9.00" }),
    runner({ no: 5, runner: "Speedy", epr: "41.0", speed: "72", edgeiqPrice: "$8.50", market: "$10.00" }),
  ],
};

const model = buildRaceIntelligenceViewModel({
  raceBook: { official: { raceKey: "2026-08-22|SANDOWN|R1" } },
  field: [],
  formGuide,
  intelligenceRace: null,
});

assert.equal(model.runnerBoard.length, 5, "all Race board runners are audited");
assert.equal(model.runnerBoard.find((row) => row.runner === "Alpha")?.epr, "50.0", "eligible active runner receives governed EPR");
assert.equal(model.runnerBoard.find((row) => row.runner === "Missing EPR")?.epr, "", "legitimate governed exclusion keeps missing EPR");
assert.equal(model.runnerBoard.find((row) => row.runner === "Alpha")?.edgeiqPrice, "$4.20", "EDGEiQ Price matches governed source");
assert.equal(model.runnerBoard.find((row) => row.runner === "Alpha")?.market, "$5.00", "market price matches market source");
assert.equal(model.runnerBoard.find((row) => row.runner === "Alpha")?.earlySpeed, "62", "governed speed matches source");
assert.deepEqual(model.topEpr.map((row) => row.runner), ["Alpha", "Bravo", "Speedy"], "EPR Top 3 excludes scratched and sorts by governed EPR");
assert.deepEqual(model.topEpr.map((row) => row.no), ["2", "3", "5"], "EPR Top 3 tie handling is deterministic by runner number");
assert.ok(!model.topEpr.some((row) => row.runner === "Scratch High"), "scratched runner is excluded from EPR Top 3");
assert.ok(!model.topEpr.some((row) => row.runner === "Missing EPR"), "missing governed EPR is excluded from EPR Top 3");
assert.equal(model.speedMap[0]?.zone, "GOVERNED SPEED", "governed evidence replaces speed-map placeholder");
assert.equal(model.speedMap[0]?.runners[0]?.runner, "Speedy", "speed preview orders existing governed speed evidence");
assert.equal(model.cards.find((card) => card.label === "TEMPO")?.value, "Insufficient Evidence", "genuine missing tempo remains a missing state");
assert.equal(model.unavailable[0], "Governed tempo field not supplied", "tempo missing state names the absent tempo field, not map evidence");
assert.equal(model.cards.find((card) => card.label === "EPF")?.value, "Insufficient Evidence", "genuine missing EPF remains a missing state");
assert.ok(model.whatMatters.length <= 3, "What Matters does not manufacture more than three statements");
assert.ok(model.whatMatters.some((item) => item.includes("Alpha:")), "governed runner evidence can populate What Matters");

const rawOnly = buildRaceIntelligenceViewModel({
  raceBook: {},
  field: [{ official: { number: 1, runner: "Historical Only" }, historicalEpi: 88.8 }],
  intelligenceRace: null,
});
assert.equal(rawOnly.runnerBoard[0]?.epr, "", "no historical EPI fallback into current EPR");

assert.equal(raceWorkspaceViewModelTestExports.compactMissing(""), "-", "missing-value formatting uses a consistent dash");
assert.ok(source.includes("topEprFromBoard"), "EPR Top 3 uses governed board values, not stale feed summaries");
assert.ok(!source.includes("Awaiting Map Evidence"), "Race view model does not conflate missing tempo with missing map evidence");

const componentSource = await readFile(path.join(repoRoot, "src", "edgeiq-os", "race", "components", "RaceIntelligenceWorkspace.tsx"), "utf8");
assert.ok(componentSource.includes("EPR TOP 3"), "Race heading is EPR TOP 3");
assert.ok(componentSource.includes("RUNNER BOARD EPR"), "Runner Board heading is EPR-labelled");
assert.ok(componentSource.includes("<th>EPR</th>"), "Runner Board column is EPR");
assert.ok(!componentSource.includes("Awaiting EPI"), "Race current-rating empty state does not say EPI");
assert.ok(!componentSource.includes("Awaiting Speed Evidence"), "Race speed preview does not blank governed partial evidence with stale speed placeholder");

const formGuideFeedSource = await readFile(path.join(repoRoot, "src", "edgeiq-os", "race", "services", "formGuideEnrichedFeed.ts"), "utf8");
const currentRaceFeedSource = await readFile(path.join(repoRoot, "src", "edgeiq-os", "race", "services", "currentRaceIntelligenceFeed.ts"), "utf8");
assert.ok(formGuideFeedSource.includes("edgeiqDataPath(\"/data/edgeiq_form_guide_enriched_v2.json\")"), "form-guide Race data request uses authoritative runtime data path");
assert.ok(formGuideFeedSource.includes("selectedRaceKey"), "form-guide Race matching accepts explicit selected race key");
assert.ok(currentRaceFeedSource.includes("edgeiqDataPath(\"/data/edgeiq_current_race_intelligence_v1.json\")"), "current Race intelligence request uses authoritative runtime data path");

console.log("EDGEIQ_RACE_TAB_VIEW_MODEL_TESTS=PASS");
console.log("ASSERTIONS=22");
