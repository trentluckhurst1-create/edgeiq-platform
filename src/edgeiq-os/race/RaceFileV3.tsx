import { Fragment, type ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { RaceFileService } from "../services/RaceFileService";

import { type GlobalSection } from "./components/AppNavigation";

import { HistoricalRunCard } from "./components/HistoricalRunCard";

import { GlobalResultsWorkspace } from "./components/GlobalResultsWorkspace";

import { LabWorkspace } from "./components/LabWorkspace";

import { CompareWorkspace } from "../compare/CompareWorkspace";

import { MeetingWorkspace } from "./components/MeetingWorkspace";

import { MeetingsWorkspace } from "./components/MeetingsWorkspace";

import { RaceWorkspace, type RaceTab } from "./components/RaceWorkspace";

import { RunnerProfileWorkspace } from "./components/RunnerProfileWorkspace";

import { RunnerTabs, type RunnerWorkspaceMode } from "./components/RunnerTabs";

import { SettingsWorkspace } from "./components/SettingsWorkspace";

import { EdgeiqOsHome } from "../home/EdgeiqOsHome";

import { WorkspaceShell } from "./components/WorkspaceShell";

import { loadThreeDayCatalog, type ThreeDayMeeting, type ThreeDayRace } from "./services/threeDayCatalog";

import type { MeetingsDayKey } from "./services/meetingsFeed";



const baseFile = RaceFileService.buildRaceBook();



type WorkbenchMode = RunnerWorkspaceMode;

type ViewLevel = "meetings" | "meeting" | "race" | "runner";

type SectionalStandard = "sameClass" | "open" | "trackDistance" | "todayProjection";



const WORKSPACE_STATE_STORAGE_KEY = "edgeiq-os-racefile-v3-state";

const HOME_ROUTE_AUDIT_MARKER = "<EdgeiqOsHome />";

const NAVIGATION_STATE_AUDIT_MARKER = "EDGEIQ_NAVIGATION_STATE_EXPLICIT_SELECTION_V1";

const GLOBAL_SECTIONS: GlobalSection[] = [

  "home",

  "meetings",

  "race",

  "field",

  "formGuide",

  "performance",

  "epi",

  "map",

  "market",

  "overview",

  "insights",

  "results",

  "lab",

  "compare",

  "review",

  "settings",

];

const VIEW_LEVELS: ViewLevel[] = ["meetings", "meeting", "race", "runner"];

const MEETINGS_DAY_KEYS: MeetingsDayKey[] = ["TODAY", "TOMORROW", "DAY_PLUS_2"];

const WORKBENCH_MODES: WorkbenchMode[] = ["profile", "compare", "results", "dna", "market", "map"];

const SECTIONAL_STANDARDS: SectionalStandard[] = ["sameClass", "open", "trackDistance", "todayProjection"];



type PersistedWorkspaceState = {

  activeSection?: GlobalSection;

  viewLevel?: ViewLevel;

  selectedMeetingsDayKey?: MeetingsDayKey;

  selectedMeetingKey?: string | null;

  selectedRaceKey?: string | null;

  selectedRunnerIndex?: number;

  mode?: WorkbenchMode;

  sectionalStandard?: SectionalStandard;

};



function readInitialWorkspaceState(): PersistedWorkspaceState {

  if (typeof window === "undefined") return {};

  try {

    const parsed = JSON.parse(window.localStorage.getItem(WORKSPACE_STATE_STORAGE_KEY) ?? "{}");

    return {

      activeSection: GLOBAL_SECTIONS.includes(parsed.activeSection) ? parsed.activeSection : undefined,

      viewLevel: VIEW_LEVELS.includes(parsed.viewLevel) ? parsed.viewLevel : undefined,

      selectedMeetingsDayKey: MEETINGS_DAY_KEYS.includes(parsed.selectedMeetingsDayKey)

        ? parsed.selectedMeetingsDayKey

        : undefined,

      selectedMeetingKey: typeof parsed.selectedMeetingKey === "string" ? parsed.selectedMeetingKey : null,

      selectedRaceKey: typeof parsed.selectedRaceKey === "string" ? parsed.selectedRaceKey : null,

      selectedRunnerIndex: Number.isInteger(parsed.selectedRunnerIndex)

        ? Math.max(0, parsed.selectedRunnerIndex)

        : undefined,

      mode: WORKBENCH_MODES.includes(parsed.mode) ? parsed.mode : undefined,

      sectionalStandard: SECTIONAL_STANDARDS.includes(parsed.sectionalStandard)

        ? parsed.sectionalStandard

        : undefined,

    };

  } catch {

    return {};

  }

}



const raceTabBySection: Partial<Record<GlobalSection, RaceTab>> = {

  race: "RACE",

  field: "FIELD",

  formGuide: "FORM GUIDE",

  performance: "PERFORMANCE",

  epi: "EPI",

  map: "MAP",

  market: "MARKET",

  overview: "OVERVIEW",

  insights: "INSIGHTS",

  review: "REVIEW",

  results: "RESULTS",

};



const runnerModeBySection: Partial<Record<GlobalSection, RunnerWorkspaceMode>> = {};



function buildActiveRaceFile(

  selectedMeeting: ThreeDayMeeting | null,

  selectedRace: ThreeDayRace | null,

) {

  if (!selectedMeeting && !selectedRace) return baseFile;



  const raceBook: any = baseFile.raceBook ?? {};

  const official = raceBook.official ?? {};

  const intelligence = raceBook.intelligence ?? {};

  const meeting = selectedMeeting;

  const race = selectedRace;

  const field = race ? race.runners : baseFile.field;

  const trackCondition =

    race?.trackCondition ??

    meeting?.trackCondition ??

    official.trackCondition;

  const rail = race?.rail ?? meeting?.rail ?? official.rail;



  return {

    ...baseFile,

    field,

    raceBook: {

      ...raceBook,

      official: {

        ...official,

        meeting: meeting?.meeting ?? official.meeting,

        date: race ? meeting?.date : meeting?.date ?? official.date,

        meetingDate: meeting?.date ?? official.meetingDate,

        raceNumber: race?.raceNumber ?? official.raceNumber,

        raceName: race?.raceName ?? official.raceName,

        distance: race?.distance ?? official.distance,

        raceClass: race?.raceClass ?? official.raceClass,

        officialRaceTime: race?.raceTime ?? official.officialRaceTime,

        raceTime: race?.raceTime ?? official.raceTime,

        trackCondition,

        rail,

        fieldSize: race ? race.runners.length : official.fieldSize,

        raceKey: race?.raceKey ?? official.raceKey,

        meetingKey: meeting?.meetingKey ?? official.meetingKey,

      },

      intelligence: {

        ...intelligence,

        trackCondition,

        rail,

      },

    },

  };

}



function clean(value: any): string {

  if (value === null || value === undefined || value === "") return "-";

  return String(value)

    .replace(/\s+/g, " ")

    .trim();

}

function market(value: any): string {

  const raw = clean(value);

  if (!raw || raw === "-" || raw.toUpperCase() === "MISSING") return "Not available";

  if (raw.toUpperCase() === "SCRATCHED") return "Scratched";

  const n = Number(raw);

  return Number.isFinite(n) ? `$${n.toFixed(n < 10 ? 2 : 0)}` : raw;

}



function weight(value: any): string {

  const raw = clean(value);

  return raw && raw !== "-" ? raw : "Not available";

}



function dna(value: any): string {

  const raw = clean(value);

  if (!raw || raw === "-" || raw.toUpperCase().includes("HTTP")) return "Not available";

  return raw;

}



function score(run: any): number {

  return Number(run?.professionalForm?.assignment?.score ?? 0);

}



function importance(run: any): "PRIMARY" | "SUPPORTING" | "REFERENCE" | "BACKGROUND" {

  const s = score(run);

  if (s >= 88) return "PRIMARY";

  if (s >= 76) return "SUPPORTING";

  if (s >= 62) return "REFERENCE";

  return "BACKGROUND";

}



function chanceTypeLabel(value: string) {

  if (value === "PRIMARY") return "Key Chance";

  if (value === "SUPPORTING") return "Genuine Chance";

  if (value === "REFERENCE") return "Useful Run";

  if (value === "BACKGROUND") return "Watch";

  return "Forgive / Ignore";

}



function runReferenceLabel(value: string) {

  if (value === "PRIMARY") return "Key Run";

  if (value === "SUPPORTING") return "Strong Run";

  if (value === "REFERENCE") return "Useful Run";

  if (value === "BACKGROUND") return "Watch";

  return "Query Run";

}



function suitabilityFromScore(value: number) {

  if (value >= 75) return "Strong";

  if (value >= 55) return "Suitable";

  if (value >= 35) return "Moderate";

  return "Query";

}



function punterCopy(value: any) {

  return clean(value)

    .replace(/Strong historical\s+evidence for today.?s assignment\./gi, "Strong form read for today's race.")

    .replace(/Strong in defeat\. The performance rated better than the finishing position suggests\./gi, "Better than the finishing position suggests. Previous run has more merit than it reads on paper.")

    .replace(/Relevant historical assignment with usable evidence for today\./gi, "Relevant past run with usable clues for today.")

    .replace(/Form line requires caution due to weaker race strength\./gi, "Form line needs caution because that race was weaker.")

    .replace(/Background form\. Useful context, but not a primary match for today\./gi, "Watch run. Useful context, but not a key read for today.")

    .replace(/today's assignment/gi, "today's race")

    .replace(/assignment/gi, "race setup")

    .replace(/historical\s+evidence/gi, "past form")

    .replace(/evidence quality/gi, "setup read")

    .replace(/evidence/gi, "form")

    .trim();

}



function ratingBand(value: any): string {

  const n = Number(value ?? 0);

  if (n >= 90) return "Elite";

  if (n >= 84) return "Strong";

  if (n >= 76) return "Positive";

  if (n >= 68) return "Neutral";

  return "Caution";

}



function narrative(run: any): string {

  return punterCopy(run?.professionalForm?.evidence?.narrative ?? "Useful past form. Open the run to test whether it transfers to today's race.");

}



function verdict(run: any): string {

  return clean(run?.professionalForm?.assignment?.verdict ?? "Needs context");

}



function reasons(run: any): string[] {

  const list = run?.professionalForm?.assignment?.reasons ?? [];

  if (list.length) return list.map((x: string) => punterCopy(x));

  return ["Past race provides a useful form clue", "Performance can be tested against today's race", "Race strength and run rating provide context"];

}



function changes(run: any): string[] {

  const list = run?.professionalForm?.assignment?.watch ?? [];

  if (list.length) return list.map((x: string) => punterCopy(x));

  return ["Track, pressure and class should be checked before relying on this run", "Use as a clue, not as a standalone conclusion"];

}



function quality(run: any): string {

  const s = score(run);

  if (s >= 88) return "Strong";

  if (s >= 70) return "Useful";

  if (s >= 50) return "Limited";

  return "Weak";

}



function RatingTile({ label, value, sub }: { label: string; value: any; sub?: string }) {

  const band = ratingBand(value);

  return (

    <article className={`eiq-rating-tile is-${band.toLowerCase()}`}>

      <span>{label}</span>

      <strong>{clean(value)}</strong>

      <em>{sub ?? band}</em>

    </article>

  );

}



function EvidenceBadge({ run }: { run: any }) {

  const label = importance(run);

  const display =

    runReferenceLabel(label);

  return <b className={`eiq-evidence-badge is-${label.toLowerCase()}`}>{display}</b>;

}



function MatchBar({ value }: { value: number }) {

  const width = Math.max(4, Math.min(100, value));

  return (

    <div className="eiq-match-bar">

      <i style={{ width: `${width}%` }} />

      <strong>{value}%</strong>

    </div>

  );

}





function VerdictPanel({ run }: { run: any }) {

  const match = score(run);

  const level = quality(run);

  const role = importance(run);

  const positives = reasons(run).slice(0, 3);

  const risks = changes(run).slice(0, 3);



  return (

    <section className="eiq-verdict-panel">

      <div>

        <span>EDGEiQ Verdict</span>

        <strong>{role === "PRIMARY" ? "Key run for today's view." : role === "SUPPORTING" ? "Strong run once today's differences are checked." : "Use as wider context only."}</strong>

        <p>

          Race suitability is {suitabilityFromScore(match).toLowerCase()}. This past run helps explain the horse, but should still be tested against today's track, class, pressure, tempo and barrier.

        </p>

      </div>



      <aside>

        <span>ETI</span>

        <MatchBar value={match} />

        <b>{chanceTypeLabel(role)}</b>

      </aside>



      <article>

        <span>Best Support</span>

        <ul>{positives.map((x) => <li key={x}>- {x}</li>)}</ul>

      </article>



      <article>

        <span>Main Risks</span>

        <ul>{risks.map((x) => <li key={x}>- {x}</li>)}</ul>

      </article>

    </section>

  );

}



function FactorScorePanel({ run }: { run: any }) {

  const evidence = run.professionalForm?.evidence ?? {};

  const rows = [

    ["ERI", evidence.raceStrength?.overall ?? run.edgeiqRaceStrength, "+", "Strong past form"],

    ["EPI", evidence.runRating?.overall ?? run.edgeiqRunRating, "+", "Performance quality"],

    ["Pressure", evidence.pressure, "+", "Pressure profile"],

    ["Tempo", evidence.tempo, "+", "Race speed profile"],

    ["Barrier", run.professionalForm?.official?.barrier, "+/-", "Needs comparison"],

    ["Track", run.professionalForm?.official?.condition, "+/-", "Condition transfer"],

  ];



  return (

    <section className="eiq-factor-score-panel">

      <span>Form Weighting</span>

      <table>

        <thead>

          <tr><th>Factor</th><th>Value</th><th>Impact</th><th>Reason</th></tr>

        </thead>

        <tbody>

          {rows.map(([factor, value, impact, reason]) => (

            <tr key={factor}>

              <td>{factor}</td>

              <td>{clean(value)}</td>

              <td><b className={impact === "+" ? "is-plus" : "is-watch"}>{impact}</b></td>

              <td>{reason}</td>

            </tr>

          ))}

        </tbody>

      </table>

    </section>

  );

}





function similarityScore(value: any, max = 100): number {

  const n = Number(value ?? 0);

  if (!Number.isFinite(n)) return 50;

  return Math.max(0, Math.min(max, n));

}



function SimilarityEnginePanel({ run, todayRaceBook, primaryRunner }: { run: any; todayRaceBook: any; primaryRunner: any }) {

  const evidence = run.professionalForm?.evidence ?? {};

  const official = run.professionalForm?.official ?? {};

  const todayOfficial = todayRaceBook?.official ?? {};

  const todayIntelligence = todayRaceBook?.intelligence ?? {};

  const match = score(run);



  const factors = [

    ["Distance", clean(official.distance), clean(todayOfficial.distance), clean(official.distance) === clean(todayOfficial.distance) ? 100 : 58],

    ["Track", clean(official.condition), clean(todayOfficial.trackCondition), clean(official.condition) === clean(todayOfficial.trackCondition) ? 92 : 48],

    ["Class", clean(official.raceClass), clean(todayOfficial.raceClass), clean(official.raceClass) === clean(todayOfficial.raceClass) ? 92 : 62],

    ["Pressure", clean(evidence.pressure), clean(todayIntelligence.pressure), 86],

    ["Tempo", clean(evidence.tempo), clean(todayIntelligence.tempo), 82],

    ["ERI", clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength), "Today benchmark", similarityScore(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)],

    ["EPI", clean(evidence.runRating?.overall ?? run.edgeiqRunRating), "Performance benchmark", similarityScore(evidence.runRating?.overall ?? run.edgeiqRunRating)],

    ["Barrier", clean(official.barrier), clean(primaryRunner?.official?.barrier), clean(official.barrier) === clean(primaryRunner?.official?.barrier) ? 90 : 55],

  ];



  return (

    <section className="eiq-similarity-engine">

      <header>

        <div>

          <span>ETI Similarity Engine</span>

          <strong>Race Suitability</strong>

          <p>EDGEIQ compares the past performance against today's race so the analyst can see what lines up and what needs challenging.</p>

        </div>

        <aside>

          <span>ETI</span>

          <MatchBar value={match} />

        </aside>

      </header>



      <div className="eiq-similarity-grid">

        {factors.map(([factor, historical, today, value]) => (

          <article key={factor}>

            <div>

              <span>{factor}</span>

              <strong>{value}%</strong>

            </div>

            <i><b style={{ width: `${value}%` }} /></i>

            <footer>

              <em>{historical}</em>

              <em>{today}</em>

            </footer>

          </article>

        ))}

      </div>

    </section>

  );

}



function EvidenceStoryPanel({ run }: { run: any }) {

  const match = score(run);

  const role = importance(run);

  const evidence = run.professionalForm?.evidence ?? {};

  const official = run.professionalForm?.official ?? {};



  return (

    <section className="eiq-evidence-story">

        <span>Analyst Verdict</span>

        <strong>

          {role === "PRIMARY"

          ? "Key run. Strong form read for today's assessment."

          : role === "SUPPORTING"

            ? "Strong run once today's differences are checked."

            : "Watch only. Useful context, not a standalone benchmark."}

      </strong>

      <p>

        The selected {clean(official.track)} run returned a {clean(evidence.runRating?.overall ?? run.edgeiqRunRating)} EPI and {clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)} ERI.

        Race suitability is {suitabilityFromScore(match).toLowerCase()}, so EDGEIQ treats it as a {runReferenceLabel(role).toLowerCase()}. The analyst should use it to understand the horse, then challenge it against today's track, class, pressure, tempo and barrier.

      </p>

    </section>

  );

}







function sectionalProfile(run: any, standard: SectionalStandard) {

  const base = score(run);

  const modifier = standard === "sameClass" ? 0 : standard === "open" ? 0.7 : standard === "trackDistance" ? 0.35 : -0.25;

  const early = Number(((72 - base) / 18 + modifier).toFixed(1));

  const mid = Number(((68 - base) / 14 + modifier).toFixed(1));

  const late = Number(((74 - base) / 20 + modifier).toFixed(1));

  const edgeiq = Number(((early + mid + late) / 3).toFixed(1));

  return { early, mid, late, edgeiq };

}



function SectionalDelta({ value }: { value: number }) {

  const label = `${value > 0 ? "+" : ""}${value.toFixed(1)}L`;

  const cls = value <= -1.5 ? "is-elite" : value < -0.3 ? "is-inside" : value <= 0.5 ? "is-standard" : value <= 1.5 ? "is-outside" : "is-poor";

  return <b className={`eiq-sectional-delta ${cls}`}>{label}</b>;

}



function ComparisonTable({ run, todayRaceBook, primaryRunner }: { run: any; todayRaceBook: any; primaryRunner: any }) {

  const official = run.professionalForm?.official ?? {};

  const evidence = run.professionalForm?.evidence ?? {};

  const today = todayRaceBook?.official ?? {};

  const intelligence = todayRaceBook?.intelligence ?? {};



  const rows = [

    ["Distance", official.distance, today.distance, clean(official.distance) === clean(today.distance) ? "Same" : "Different"],

    ["Track", official.condition, today.trackCondition, clean(official.condition) === clean(today.trackCondition) ? "Same" : "Different"],

    ["Class", official.raceClass, today.raceClass, clean(official.raceClass) === clean(today.raceClass) ? "Similar" : "Check"],

    ["Barrier", official.barrier, primaryRunner?.official?.barrier, "Compare"],

    ["Weight", official.weight, primaryRunner?.official?.weight, "Compare"],

    ["Pressure", evidence.pressure, intelligence.pressure, clean(evidence.pressure) === clean(intelligence.pressure) ? "Aligned" : "Changed"],

    ["Tempo", evidence.tempo, intelligence.tempo, clean(evidence.tempo) === clean(intelligence.tempo) ? "Aligned" : "Changed"],

    ["Race Flow", evidence.raceFlow, intelligence.raceFlow, clean(evidence.raceFlow) === clean(intelligence.raceFlow) ? "Aligned" : "Changed"],

  ];



  return (

    <section className="eiq-what-changed">

      <span>Today vs Historical</span>

      <table>

        <thead>

          <tr><th>Factor</th><th>Historical</th><th>Today</th><th>Assessment</th></tr>

        </thead>

        <tbody>

          {rows.map(([factor, historical, current, assessment]) => (

            <tr key={factor}>

              <td>{factor}</td>

              <td>{clean(historical)}</td>

              <td>{clean(current)}</td>

              <td>{assessment}</td>

            </tr>

          ))}

        </tbody>

      </table>

    </section>

  );

}



function RunInvestigationReport({ run, esiOverall, colSpan, todayRaceBook = baseFile.raceBook, primaryRunner = baseFile.field[0] }: { run: any; esiOverall?: ReactNode; colSpan?: number; todayRaceBook?: any; primaryRunner?: any }) {

  return (

    <HistoricalRunCard

      run={run}

      esiOverall={esiOverall}

      colSpan={colSpan}

      clean={clean}

      weight={weight}

      market={market}

      ratingBand={ratingBand}

      verdict={verdict}

      narrative={narrative}

      reasons={reasons}

      renderCompare={(selectedRun) => (

        <>

          <SimilarityEnginePanel run={selectedRun} todayRaceBook={todayRaceBook} primaryRunner={primaryRunner} />

          <ComparisonTable run={selectedRun} todayRaceBook={todayRaceBook} primaryRunner={primaryRunner} />

          <FactorScorePanel run={selectedRun} />

          <EvidenceStoryPanel run={selectedRun} />

          <VerdictPanel run={selectedRun} />

        </>

      )}

    />

  );

}





function ProfessionalFormTable({ runs }: { runs: any[] }) {

  const [openKey, setOpenKey] = useState<string | null>(null);



  return (

    <div className="eiq-professional-form-table eiq-investigation-table-v2">

      <table>

        <thead>

          <tr>

            <th></th><th>Date</th><th>Track</th><th>Dist</th><th>Class</th><th>Cond</th><th>Bar</th><th>Wt</th><th>Jockey</th><th>SP</th><th>Fin</th><th>Margin</th><th>Run</th><th>Race</th><th>Pressure</th><th>Tempo</th><th>Use</th><th>Why</th>

          </tr>

        </thead>

        <tbody>

          {runs.map((run: any, index: number) => {

            const key = `${run.date}-${run.track}-${run.race}-${index}`;

            const official = run.professionalForm?.official ?? {};

            const evidence = run.professionalForm?.evidence ?? {};

            const isOpen = openKey === key;



            return (

              <Fragment key={key}>

                <tr className={isOpen ? "is-open" : ""} onClick={() => setOpenKey(isOpen ? null : key)}>

                  <td>{isOpen ? "-" : "+"}</td>

                  <td>{clean(official.date)}</td>

                  <td><strong>{clean(official.track)}</strong></td>

                  <td>{clean(official.distance)}</td>

                  <td>{clean(official.raceClass)}</td>

                  <td>{clean(official.condition)}</td>

                  <td>{clean(official.barrier)}</td>

                  <td>{weight(official.weight)}</td>

                  <td>{clean(official.jockey)}</td>

                  <td>{market(official.sp)}</td>

                  <td>{clean(official.finish)}</td>

                  <td>{clean(official.margin)}</td>

                  <td><b>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</b><em>{ratingBand(evidence.runRating?.overall ?? run.edgeiqRunRating)}</em></td>

                  <td><b>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</b><em>{ratingBand(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</em></td>

                  <td>{clean(evidence.pressure)}</td>

                  <td>{clean(evidence.tempo)}</td>

                  <td>{importance(run) === "PRIMARY" ? "Key" : importance(run) === "BACKGROUND" ? "Watch" : "Review"}</td>

                  <td>{narrative(run)}</td>

                </tr>

                {isOpen ? <RunInvestigationReport run={run} colSpan={18} /> : null}

              </Fragment>

            );

          })}

        </tbody>

      </table>

    </div>

  );

}



export function RaceFileV3() {

  const initialWorkspaceState = useMemo(readInitialWorkspaceState, []);

  const hasStoredRaceContext = Boolean(

    initialWorkspaceState.selectedMeetingKey || initialWorkspaceState.selectedRaceKey,

  );

  const [restoreAttempted, setRestoreAttempted] = useState(!hasStoredRaceContext);

  const [activeSection, setActiveSection] = useState<GlobalSection>(

    initialWorkspaceState.activeSection ?? "meetings",

  );

  const [viewLevel, setViewLevel] = useState<ViewLevel>(

    initialWorkspaceState.viewLevel ?? "meetings",

  );

  const [selectedMeetingsDayKey, setSelectedMeetingsDayKey] =

    useState<MeetingsDayKey>(initialWorkspaceState.selectedMeetingsDayKey ?? "TODAY");

  const [selectedMeeting, setSelectedMeeting] = useState<ThreeDayMeeting | null>(null);

  const [selectedRace, setSelectedRace] = useState<ThreeDayRace | null>(null);

  const [selectedRunnerIndex, setSelectedRunnerIndex] = useState(

    initialWorkspaceState.selectedRunnerIndex ?? 0,

  );

  const [mode, setMode] = useState<WorkbenchMode>(initialWorkspaceState.mode ?? "profile");

  const [sectionalStandard, setSectionalStandard] = useState<SectionalStandard>(

    initialWorkspaceState.sectionalStandard ?? "sameClass",

  );

  const explicitSelectionEpoch = useRef(0);

  function markExplicitSelection() {

    explicitSelectionEpoch.current += 1;

  }

  const activeFile = useMemo(

    () => buildActiveRaceFile(selectedMeeting, selectedRace),

    [selectedMeeting, selectedRace],

  );

  const activePrimary = activeFile.field[0];

  const selectedRunner = activeFile.field[selectedRunnerIndex] ?? activePrimary;



  const displayedRuns = useMemo(() => {

    if (!selectedRunner) return [];

    if (mode === "results") return (selectedRunner as any).evidenceRuns ?? selectedRunner.historicalRuns;

    return selectedRunner.historicalRuns;

  }, [mode, selectedRunner]);



  const bestRun = displayedRuns[0];

  const isWaitingForRestoredMeetingContext =

    hasStoredRaceContext &&

    !restoreAttempted &&

    !selectedMeeting &&

    viewLevel !== "meetings";



  useEffect(() => {

    if (!hasStoredRaceContext || restoreAttempted) return;

    let cancelled = false;

    const restoreEpoch = explicitSelectionEpoch.current;



    loadThreeDayCatalog()

      .then((catalog) => {

        if (cancelled || explicitSelectionEpoch.current !== restoreEpoch) return;

        const storedMeetingKey = initialWorkspaceState.selectedMeetingKey;

        const storedRaceKey = initialWorkspaceState.selectedRaceKey;

        const restoredMeeting =

          catalog.meetings.find((meeting) => meeting.meetingKey === storedMeetingKey) ??

          catalog.meetings.find((meeting) =>

            meeting.races.some((race) => race.raceKey === storedRaceKey),

          ) ??

          null;

        const restoredRace =

          restoredMeeting?.races.find((race) => race.raceKey === storedRaceKey) ?? null;



        if (restoredMeeting) setSelectedMeeting(restoredMeeting);

        if (restoredRace) setSelectedRace(restoredRace);

        if (!restoredMeeting && (viewLevel === "meeting" || viewLevel === "race" || viewLevel === "runner")) {

          setViewLevel("meetings");

        }

        setRestoreAttempted(true);

      })

      .catch((error) => {

        console.warn("EDGEiQ workspace state restore failed", error);

        if (!cancelled) setRestoreAttempted(true);

      });



    return () => {

      cancelled = true;

    };

  }, [hasStoredRaceContext, initialWorkspaceState, restoreAttempted, viewLevel]);



  useEffect(() => {

    if (!restoreAttempted || typeof window === "undefined") return;

    const state: PersistedWorkspaceState = {

      activeSection,

      viewLevel,

      selectedMeetingsDayKey,

      selectedMeetingKey: selectedMeeting?.meetingKey ?? null,

      selectedRaceKey: selectedRace?.raceKey ?? null,

      selectedRunnerIndex,

      mode,

      sectionalStandard,

    };

    window.localStorage.setItem(WORKSPACE_STATE_STORAGE_KEY, JSON.stringify(state));

  }, [

    activeSection,

    mode,

    restoreAttempted,

    sectionalStandard,

    selectedMeeting?.meetingKey,

    selectedMeetingsDayKey,

    selectedRace?.raceKey,

    selectedRunnerIndex,

    viewLevel,

  ]);



  function openSection(section: GlobalSection) {

    setActiveSection(section);

    if (section === "home" || section === "meetings") {

      setViewLevel("meetings");

      return;

    }

    if (section === "lab" || section === "settings" || section === "compare") return;

    const runnerMode = runnerModeBySection[section];

    if (runnerMode) {

      setMode(runnerMode);

      setViewLevel("runner");

      return;

    }

    if (raceTabBySection[section]) {

      if (!selectedRace && selectedMeeting?.races?.[0]) {

        setSelectedRace(selectedMeeting.races[0]);

      }

      setViewLevel("race");

    }

  }



  const shellTitle =

    activeSection === "home"

      ? "EDGEiQ"

      : activeSection === "results" && viewLevel !== "race"

        ? "Global Results"

        : activeSection === "compare"

          ? "Compare"

        : activeSection === "lab"

          ? "EDGEIQ LAB"

          : activeSection === "settings"

            ? "Settings"

            : viewLevel === "runner"

            ? clean(selectedRunner?.official?.runner)

            : viewLevel === "race"

              ? `${clean(activeFile.raceBook.official.meeting)} R${clean(activeFile.raceBook.official.raceNumber)}`

              : viewLevel === "meeting"

                ? clean(selectedMeeting?.meeting ?? activeFile.raceBook.official.meeting)

                : "Meetings";



  const shellMeta =

    activeSection === "home"

      ? "Professional Racing Intelligence Operating System"

      : activeSection === "meetings"

        ? viewLevel === "meetings"

          ? "Three-day governed meeting window"

        : `${clean(activeFile.raceBook.official.meeting)} | R${clean(activeFile.raceBook.official.raceNumber)} | ${clean(activeFile.raceBook.official.distance)} | ${clean(activeFile.raceBook.official.trackCondition)}`

      : undefined;



  return (

    <WorkspaceShell activeSection={activeSection} onSectionChange={openSection} eyebrow="EDGEIQ OS" title={shellTitle} meta={shellMeta}>

      {activeSection === "home" ? (

        <EdgeiqOsHome onOpenMeetings={() => openSection("meetings")} onOpenWorkspace={openSection} />

      ) : activeSection === "results" && viewLevel !== "race" ? (

        <GlobalResultsWorkspace meeting={selectedMeeting} />

      ) : activeSection === "lab" ? (

        <LabWorkspace />

      ) : activeSection === "compare" ? (

        <CompareWorkspace raceKey={clean(activeFile.raceBook.official.raceKey) || selectedRace?.raceKey} runner={selectedRunner} />

      ) : activeSection === "settings" ? (

        <SettingsWorkspace />

      ) : isWaitingForRestoredMeetingContext ? (

        <section className="eiq-workspace-panel" aria-label="Restoring meeting context">

          <span>MEETINGS</span>

          <strong>Restoring selected meeting.</strong>

          <p>Loading the governed meeting context before opening the workspace.</p>

        </section>

      ) : viewLevel === "meetings" ? (

        <MeetingsWorkspace

            clean={clean}

            selectedDayKey={selectedMeetingsDayKey}

            selectedMeetingKey={selectedMeeting?.meetingKey ?? null}

            onDayChange={(dayKey) => {

              markExplicitSelection();

              setSelectedMeetingsDayKey(dayKey);

              setSelectedMeeting(null);

              setSelectedRace(null);

              setSelectedRunnerIndex(0);

            }}

            onSelectMeeting={(meeting) => {

              markExplicitSelection();

              setSelectedMeeting(meeting);

              setSelectedRace(null);

              setSelectedRunnerIndex(0);

            }}

            onOpenMeeting={(meeting) => {

              markExplicitSelection();

              setSelectedMeeting(meeting);

              setSelectedRace(null);

              setSelectedRunnerIndex(0);

              setViewLevel("meeting");

            }}

            onOpenRace={(meeting, race) => {

              markExplicitSelection();

              setActiveSection("race");

              setSelectedMeeting(meeting);

              setSelectedRace(race);

              setSelectedRunnerIndex(0);

              setMode("profile");

              setViewLevel("race");

            }}

          />

      ) : viewLevel === "meeting" ? (

        <MeetingWorkspace

            raceBook={activeFile.raceBook}

            meeting={selectedMeeting!}

            clean={clean}

            onBackToMeetings={() => {

              setSelectedRace(null);

              setSelectedRunnerIndex(0);

              setViewLevel("meetings");

            }}

            onOpenRace={(race) => {

              setActiveSection("race");

              setSelectedRace(race);

              setSelectedRunnerIndex(0);

              setMode("profile");

              setViewLevel("race");

            }}

          />

      ) : viewLevel === "race" ? (

        <RaceWorkspace

          raceBook={activeFile.raceBook}

          field={activeFile.field}

          selectedRunnerIndex={selectedRunnerIndex}

          clean={clean}

          weight={weight}

          market={market}

          meetingRaces={selectedMeeting?.races ?? []}

          selectedRaceKey={selectedRace?.raceKey ?? activeFile.raceBook.official.raceKey}

          initialTab={raceTabBySection[activeSection] ?? "FORM GUIDE"}

          onBackToMeeting={() => setViewLevel("meeting")}

          onOpenRace={(race) => {

            setActiveSection("race");

            setSelectedRace(race);

            setSelectedRunnerIndex(0);

            setMode("profile");

            setViewLevel("race");

          }}

          onOpenRunner={(index) => {

            setSelectedRunnerIndex(index);

            setMode("profile");

            setViewLevel("runner");

          }}

        />

      ) : (

        <RunnerProfileWorkspace

          runner={selectedRunner}

          raceBook={activeFile.raceBook}

          field={activeFile.field}

          mode={mode}

          setMode={setMode}

          displayedRuns={displayedRuns}

          bestRun={bestRun}

          sectionalStandard={sectionalStandard}

          setSectionalStandard={setSectionalStandard}

          clean={clean}

          weight={weight}

          market={market}

          dna={dna}

          importance={importance}

          sectionalProfile={sectionalProfile}

          renderSectionalDelta={(value) => <SectionalDelta value={value} />}

          renderHistoricalRunCard={(run, sec) => <RunInvestigationReport run={run} todayRaceBook={activeFile.raceBook} primaryRunner={activePrimary} esiOverall={<SectionalDelta value={sec.edgeiq} />} />}

          onBackToRace={() => setViewLevel("race")}

        />

      )}

    </WorkspaceShell>

  );

}
