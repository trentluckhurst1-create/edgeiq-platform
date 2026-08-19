from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PRESENTATION = ROOT / "src" / "edgeiq-os" / "design-system" / "presentation.ts"
RACE_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
RACE_INTEL = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
VIEW_MODEL = ROOT / "src" / "edgeiq-os" / "race" / "services" / "raceWorkspaceViewModel.ts"
RACE_FILE_V3 = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"


def patch_presentation() -> None:
    text = PRESENTATION.read_text(encoding="utf-8")
    if "canonicalRaceTitleDisplay" in text:
        return
    text += '''

const PROMOTIONAL_RACE_TITLE_PATTERNS: Array<[RegExp, string]> = [
  [/\\bLADBROKES\\s+SALE\\s+CUP\\s+25TH\\s+OCTOBER\\s*[\\u2013\\u2014-]?\\s*BOOK\\s+NOW\\s*/gi, "Sale Cup "],
  [/\\bTHANKYOU\\s+MEMBERS\\s*&\\s*SPONSORS\\s+FOR\\s+SEASON\\s+2025\\/?26\\s*/gi, ""],
  [/\\bLADBROKES\\s+PLACE\\s+EXTRA\\s+TO\\s+10TH\\s*/gi, ""],
  [/\\bLADBROKES\\s+ODDS\\s+SURGE\\s*/gi, ""],
  [/\\bBOOK\\s+NOW\\b/gi, ""],
  [/\\bBET\\s+NOW\\b/gi, ""],
  [/\\bODDS\\s+SURGE\\b/gi, ""],
  [/\\bPLACE\\s+EXTRA\\b/gi, ""],
  [/\\bMEMBERS\\s*&\\s*SPONSORS\\s+FOR\\s+SEASON\\s+2025\\/?26\\b/gi, ""],
];

export function canonicalRaceTitleDisplay(value: unknown): string {
  let text = cleanProductText(value, "");
  if (!text) return "";
  for (const [pattern, replacement] of PROMOTIONAL_RACE_TITLE_PATTERNS) {
    text = text.replace(pattern, replacement);
  }
  return text.replace(/\\s*[\\u2013\\u2014-]\\s*$/g, "").replace(/\\s{2,}/g, " ").trim();
}
'''
    PRESENTATION.write_text(text, encoding="utf-8")


def patch_race_workspace() -> None:
    text = RACE_WORKSPACE.read_text(encoding="utf-8")
    text = text.replace(
        'import { canonicalTrackDisplayName } from "../../design-system/presentation";',
        'import { canonicalRaceTitleDisplay, canonicalTrackDisplayName } from "../../design-system/presentation";',
    )
    text = text.replace('initialTab = "FORM GUIDE",', 'initialTab = "RACE",')
    text = text.replace(
        'const raceTitle = headerValue(official.raceName) || headerValue(official.name);',
        'const raceTitle = canonicalRaceTitleDisplay(headerValue(official.raceName) || headerValue(official.name));',
    )
    text = text.replace(
        """          clean={clean}
        />""",
        """          clean={clean}
          onBackToMeeting={onBackToMeeting}
          onOpenRace={onOpenRace}
        />""",
        1,
    )
    RACE_WORKSPACE.write_text(text, encoding="utf-8")


def patch_racefile_routing() -> None:
    text = RACE_FILE_V3.read_text(encoding="utf-8")
    text = text.replace(
        """            onOpenRace={(meeting, race) => {

              markExplicitSelection();

              setSelectedMeeting(meeting);""",
        """            onOpenRace={(meeting, race) => {

              markExplicitSelection();

              setActiveSection("race");

              setSelectedMeeting(meeting);""",
    )
    text = text.replace(
        """            onOpenRace={(race) => {

              setSelectedRace(race);""",
        """            onOpenRace={(race) => {

              setActiveSection("race");

              setSelectedRace(race);""",
    )
    text = text.replace(
        """          onOpenRace={(race) => {

            setSelectedRace(race);""",
        """          onOpenRace={(race) => {

            setActiveSection("race");

            setSelectedRace(race);""",
    )
    RACE_FILE_V3.write_text(text, encoding="utf-8")


def write_view_model() -> None:
    VIEW_MODEL.write_text(r'''import type { FormGuideRaceDisplay, FormGuideRunnerDisplay } from "./formGuideNormaliser";
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
''', encoding="utf-8")


def write_race_intelligence() -> None:
    RACE_INTEL.write_text(r'''import { useEffect, useMemo, useState } from "react";
import { buildRaceIntelligenceViewModel } from "../services/raceWorkspaceViewModel";
import { findCurrentRaceIntelligenceRace, loadCurrentRaceIntelligenceFeed, type CurrentRaceIntelligenceRace } from "../services/currentRaceIntelligenceFeed";
import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";
import type { ThreeDayRace } from "../services/threeDayCatalog";
import { canonicalRaceTitleDisplay, canonicalRailDisplay, canonicalTrackDisplayName, canonicalTrackRatingDisplay, canonicalWeatherDisplay, cleanProductText } from "../../design-system/presentation";

type Props = {
  raceBook: any;
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  raceKey?: string | null;
  meetingRaces?: ThreeDayRace[];
  clean: (value: any) => string;
  onBackToMeeting?: () => void;
  onOpenRace?: (race: ThreeDayRace) => void;
};

function text(value: unknown, fallback = ""): string {
  return cleanProductText(value, fallback);
}

function firstValue(source: unknown, keys: string[]): unknown {
  if (!source || typeof source !== "object") return undefined;
  for (const key of keys) {
    const value = key.split(".").reduce((acc: any, part) => acc?.[part], source as any);
    if (value !== undefined && value !== null && String(value).trim() !== "") return value;
  }
  return undefined;
}

function money(value: unknown): string {
  const raw = text(value, "").replace(/[$,]/g, "");
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? `$${parsed.toLocaleString("en-AU", { maximumFractionDigits: 0 })}` : "";
}

function formatDate(value: unknown): string {
  const raw = text(value, "");
  if (!raw) return "";
  const date = new Date(`${raw}T00:00:00`);
  return Number.isNaN(date.getTime()) ? raw : new Intl.DateTimeFormat("en-AU", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function formatTime(value: unknown): string {
  const raw = text(value, "");
  if (!raw) return "";
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return new Intl.DateTimeFormat("en-AU", { hour: "numeric", minute: "2-digit", hour12: true, timeZone: "Australia/Melbourne" }).format(parsed);
}

function cell(value: unknown, fallback = "—"): string {
  return text(value, fallback);
}

function Silk({ src, runner }: { src: string; runner: string }) {
  return src ? <img className="eiq-race-v1__silk" src={src} alt={`${runner} silks`} loading="lazy" onError={(event) => { event.currentTarget.style.display = "none"; }} /> : <span className="eiq-race-v1__silk is-empty" aria-hidden="true" />;
}

export function RaceIntelligenceWorkspace({ raceBook, field, formGuide, raceKey, meetingRaces = [], clean, onBackToMeeting, onOpenRace }: Props) {
  const [intelligenceRace, setIntelligenceRace] = useState<CurrentRaceIntelligenceRace | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadCurrentRaceIntelligenceFeed()
      .then((payload) => {
        if (!cancelled) setIntelligenceRace(findCurrentRaceIntelligenceRace(payload, raceKey));
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn("Current race intelligence feed not loaded", error);
          setIntelligenceRace(null);
        }
      });
    return () => { cancelled = true; };
  }, [raceKey]);

  const model = useMemo(() => buildRaceIntelligenceViewModel({ raceBook, field, formGuide, intelligenceRace }), [raceBook, field, formGuide, intelligenceRace]);
  const official = raceBook?.official ?? {};
  const source = raceBook?.source ?? {};
  const meeting = canonicalTrackDisplayName(clean(official.meeting));
  const raceNo = clean(official.raceNumber);
  const raceName = canonicalRaceTitleDisplay(clean(official.raceName) || clean(firstValue(source, ["raceName", "name"])) || `Race ${raceNo}`);
  const raceClass = clean(official.raceClass) || clean(firstValue(source, ["raceClass", "class"]));
  const distance = clean(official.distance) || clean(firstValue(source, ["distance"]));
  const track = canonicalTrackRatingDisplay(official.trackCondition || firstValue(source, ["trackCondition", "condition", "conditions"]), "Track Rating Awaiting");
  const rail = canonicalRailDisplay(official.rail || firstValue(source, ["rail", "railPosition"]), "Rail Not Supplied");
  const time = formatTime(official.raceTime || official.officialRaceTime || firstValue(source, ["raceTime", "time"])) || "Time Not Published";
  const date = formatDate(official.date || official.meetingDate || firstValue(source, ["date", "raceDate"])) || "Date Not Published";
  const prize = money(firstValue(source, ["prizeMoney", "prizemoney", "totalPrizeMoney"]) ?? official.prizeMoney) || "Prizemoney Not Published";
  const weather = canonicalWeatherDisplay(firstValue(source, ["weather", "weatherCondition", "forecast"]), "Weather Awaiting Feed");
  const status = clean(firstValue(official, ["status"]) ?? firstValue(source, ["status"])) || "Active";
  const selectedRaceKey = text(raceKey, "");
  const races = [...meetingRaces].sort((a, b) => Number(a.raceNumber) - Number(b.raceNumber));
  const activeRunnerCount = model.runnerBoard.filter((runner) => !runner.scratched).length;
  const metadata = [["MEETING", meeting || "Meeting Not Published"], ["DATE", date], ["TIME", time], ["DISTANCE", distance || "Distance Not Published"], ["TRACK", track], ["RAIL", rail], ["WEATHER", weather], ["PRIZEMONEY", prize]];

  return (
    <section className="eiq-race-v1" aria-label="Race overview" data-edgeiq-race-workspace-v1="locked">
      <div className="eiq-race-v1__breadcrumb" aria-label="Race breadcrumb">
        <button type="button" onClick={onBackToMeeting}>MEETINGS</button><span aria-hidden="true">&gt;</span><strong>{meeting || "MEETING"}</strong><span aria-hidden="true">&gt;</span><strong>RACE {raceNo || "—"}</strong><span aria-hidden="true">&gt;</span><strong>RACE</strong>
      </div>
      <header className="eiq-race-v1__identity">
        <div><h1><span>Race {raceNo || "—"}</span> {raceName}</h1>{raceClass ? <span className="eiq-race-v1__class-badge">{raceClass}</span> : null}</div>
        <button type="button" className="eiq-approved-button" onClick={onBackToMeeting}>Back to Races</button>
      </header>
      <dl className="eiq-race-v1__metadata" aria-label="Race metadata">{metadata.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      {races.length ? <section className="eiq-race-v1__selector" aria-label="Races at this meeting"><span>RACES AT THIS MEETING</span><div>{races.map((race) => {
        const isSelected = String(race.raceKey) === selectedRaceKey;
        return <button key={race.raceKey} type="button" className={isSelected ? "is-active" : ""} aria-current={isSelected ? "true" : undefined} onClick={() => onOpenRace?.(race)}><strong>R{race.raceNumber}</strong><small>{formatTime(race.raceTime) || "Time Not Published"}</small></button>;
      })}</div></section> : null}
      <section className="eiq-race-v1__summary" aria-label="Race intelligence summary">{model.cards.map((card) => <article key={card.label} className="eiq-race-v1__summary-card"><span>{card.label}</span><strong>{card.value}</strong><p>{card.detail}</p></article>)}</section>
      <section className="eiq-race-v1__matters" aria-label="What matters today"><header><h2>WHAT MATTERS TODAY</h2><span>{activeRunnerCount ? `${activeRunnerCount} active` : `${model.runnerBoard.length} runners`}</span></header><div>{model.whatMatters.length ? model.whatMatters.slice(0, 5).map((item, index) => <p key={`${item}-${index}`}><span aria-hidden="true" />{item}</p>) : <p><span aria-hidden="true" />Insufficient governed race statements for this race.</p>}</div></section>
      <section className="eiq-race-v1__midrow">
        <article className="eiq-race-v1__speed" aria-label="Speed map preview"><header><h2>SPEED MAP PREVIEW</h2><span>Travel right to left</span></header>{model.speedMap.some((zone) => zone.runners.length) ? <div className="eiq-race-v1__speed-grid">{model.speedMap.map((zone) => <div key={zone.zone} className="eiq-race-v1__speed-zone"><strong>{zone.zone}</strong><div>{zone.runners.length ? zone.runners.slice(0, 5).map((runner) => <span key={`${zone.zone}-${runner.no}-${runner.runner}`}><b>{runner.no}</b>{runner.runner}{runner.earlySpeed ? <em>{runner.earlySpeed}</em> : null}</span>) : <small>Awaiting Speed Evidence</small>}</div></div>)}</div> : <div className="eiq-race-v1__empty">Awaiting Speed Evidence</div>}</article>
        <article className="eiq-race-v1__epi" aria-label="EPI top 3"><header><h2>EPI TOP 3</h2><span>{model.topEpi.length ? "Governed EPI" : "Insufficient Evidence"}</span></header><div>{[0, 1, 2].map((index) => {
          const row = model.topEpi[index];
          return row ? <div key={`${row.no}-${row.runner}`} className="eiq-race-v1__epi-row"><b>{index + 1}</b><span>{row.no}</span><strong>{row.runner}</strong><em>{row.value}</em><small>{row.status}</small></div> : <div key={`empty-epi-${index}`} className="eiq-race-v1__epi-row is-empty"><b>{index + 1}</b><span>—</span><strong>Insufficient Evidence</strong><em>—</em><small>Awaiting EPI</small></div>;
        })}</div></article>
      </section>
      <section className="eiq-race-v1__conditions" aria-label="Race conditions"><h2>RACE CONDITIONS</h2><dl>{[["Class", raceClass], ["Distance", distance], ["Track", track], ["Rail", rail], ["Status", status]].filter(([, value]) => text(value, "")).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>
      <section className="eiq-race-v1__board" aria-label="Runner board"><header><h2>RUNNER BOARD</h2><span>{model.runnerBoard.length ? `${model.runnerBoard.length} runners` : "Field Not Published"}</span></header><div className="eiq-race-v1__table-wrap"><table className="eiq-race-v1__table"><colgroup><col className="col-no" /><col className="col-silk" /><col className="col-runner" /><col className="col-bar" /><col className="col-wgt" /><col className="col-jockey" /><col className="col-trainer" /><col className="col-epi" /><col className="col-speed" /><col className="col-edgeiq" /><col className="col-market" /><col className="col-status" /></colgroup><thead><tr><th>NO</th><th>SILK</th><th className="is-left">RUNNER</th><th>BAR</th><th>WGT</th><th className="is-left">JOCKEY</th><th className="is-left">TRAINER</th><th>EPI</th><th>EARLY SPEED</th><th>EDGEIQ PRICE</th><th>MARKET</th><th>STATUS</th></tr></thead><tbody>{model.runnerBoard.length ? model.runnerBoard.map((runner) => <tr key={`${runner.no}-${runner.runner}`} className={runner.scratched ? "is-scratched" : ""}><td>{cell(runner.no)}</td><td><Silk src={runner.silkUrl} runner={runner.runner} /></td><td className="is-left"><strong>{cell(runner.runner)}</strong></td><td>{cell(runner.barrier)}</td><td>{cell(runner.weight)}</td><td className="is-left">{cell(runner.jockey)}</td><td className="is-left">{cell(runner.trainer)}</td><td>{runner.scratched ? "—" : cell(runner.epi)}</td><td>{runner.scratched ? "—" : cell(runner.earlySpeed)}</td><td>{runner.scratched ? "—" : cell(runner.edgeiqPrice)}</td><td>{runner.scratched ? "Scratched" : cell(runner.market, "Awaiting Market")}</td><td><span className="eiq-race-v1__status">{runner.status}</span></td></tr>) : <tr><td colSpan={12}>Field Not Published</td></tr>}</tbody></table></div></section>
    </section>
  );
}
''', encoding="utf-8")


CSS_BLOCK = r'''

/* EDGEIQ RACE WORKSPACE V1 LOCKED SPECIFICATION */
.edgeiq-os .eiq-race-v1 { display: grid !important; gap: 12px !important; color: var(--eiq-product-text) !important; }
.edgeiq-os .eiq-race-v1__breadcrumb { min-height: 24px !important; display: flex !important; align-items: center !important; gap: 8px !important; color: var(--eiq-product-muted) !important; font-size: 12px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__breadcrumb button { min-height: 24px !important; padding: 0 !important; border: 0 !important; background: transparent !important; color: var(--eiq-product-blue) !important; font-size: 12px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__breadcrumb strong { color: var(--eiq-product-muted) !important; font-size: 12px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__identity, .edgeiq-os .eiq-race-v1__matters, .edgeiq-os .eiq-race-v1__speed, .edgeiq-os .eiq-race-v1__epi, .edgeiq-os .eiq-race-v1__conditions, .edgeiq-os .eiq-race-v1__board, .edgeiq-os .eiq-race-v1__selector { background: var(--eiq-product-panel) !important; border: 1px solid var(--eiq-product-border) !important; border-radius: var(--eiq-product-radius) !important; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important; }
.edgeiq-os .eiq-race-v1__identity { min-height: 58px !important; display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 16px !important; padding: 12px 16px !important; }
.edgeiq-os .eiq-race-v1__identity > div { min-width: 0 !important; display: flex !important; align-items: center !important; gap: 12px !important; flex-wrap: wrap !important; }
.edgeiq-os .eiq-race-v1__identity h1 { margin: 0 !important; color: var(--eiq-product-text) !important; font-size: 24px !important; line-height: 30px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__identity h1 span { display: inline !important; margin-right: 10px !important; color: var(--eiq-product-muted) !important; font-size: 24px !important; line-height: 30px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__class-badge { min-height: 28px !important; display: inline-flex !important; align-items: center !important; padding: 0 10px !important; border: 1px solid rgba(36, 86, 184, 0.22) !important; border-radius: 8px !important; background: #eef4ff !important; color: var(--eiq-product-blue) !important; font-size: 12px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__identity .eiq-approved-button { min-height: 36px !important; padding: 0 14px !important; border: 1px solid var(--eiq-product-blue) !important; background: #ffffff !important; color: var(--eiq-product-blue) !important; font-size: 13px !important; font-weight: 700 !important; white-space: nowrap !important; }
.edgeiq-os .eiq-race-v1__metadata { min-height: 42px !important; margin: 0 !important; display: grid !important; grid-template-columns: repeat(8, minmax(110px, 1fr)) !important; border: 1px solid var(--eiq-product-border) !important; border-radius: var(--eiq-product-radius) !important; background: var(--eiq-product-panel) !important; overflow: hidden !important; }
.edgeiq-os .eiq-race-v1__metadata div { min-height: 42px !important; display: grid !important; align-content: center !important; gap: 2px !important; padding: 8px 12px !important; border-right: 1px solid var(--eiq-product-border-soft) !important; }
.edgeiq-os .eiq-race-v1__metadata div:last-child { border-right: 0 !important; }
.edgeiq-os .eiq-race-v1__metadata dt { color: var(--eiq-product-muted) !important; font-size: 11px !important; line-height: 14px !important; font-weight: 700 !important; text-transform: uppercase !important; }
.edgeiq-os .eiq-race-v1__metadata dd { margin: 0 !important; color: var(--eiq-product-text) !important; font-size: 13px !important; line-height: 16px !important; font-weight: 700 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
.edgeiq-os .eiq-race-v1__selector { min-height: 48px !important; display: flex !important; align-items: center !important; gap: 12px !important; padding: 8px 10px !important; }
.edgeiq-os .eiq-race-v1__selector > span { flex: 0 0 auto !important; color: var(--eiq-product-muted) !important; font-size: 12px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__selector > div { min-width: 0 !important; display: flex !important; gap: 8px !important; overflow-x: auto !important; padding-bottom: 2px !important; }
.edgeiq-os .eiq-race-v1__selector button { flex: 0 0 auto !important; min-width: 72px !important; min-height: 34px !important; display: grid !important; align-content: center !important; gap: 1px !important; padding: 0 10px !important; border: 1px solid var(--eiq-product-border) !important; background: #ffffff !important; color: var(--eiq-product-text) !important; border-radius: 8px !important; }
.edgeiq-os .eiq-race-v1__selector button.is-active { border-color: var(--eiq-product-blue) !important; background: #eef4ff !important; color: var(--eiq-product-blue) !important; }
.edgeiq-os .eiq-race-v1__selector button strong, .edgeiq-os .eiq-race-v1__selector button small { margin: 0 !important; font-size: 12px !important; line-height: 14px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__selector button small { color: var(--eiq-product-muted) !important; font-weight: 500 !important; }
.edgeiq-os .eiq-race-v1__summary { display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 10px !important; }
.edgeiq-os .eiq-race-v1__summary-card { min-height: 112px !important; display: grid !important; align-content: start !important; gap: 7px !important; padding: 14px !important; border: 1px solid var(--eiq-product-border) !important; border-radius: var(--eiq-product-radius) !important; background: var(--eiq-product-panel) !important; }
.edgeiq-os .eiq-race-v1__summary-card span, .edgeiq-os .eiq-race-v1__speed header span, .edgeiq-os .eiq-race-v1__epi header span, .edgeiq-os .eiq-race-v1__board header span, .edgeiq-os .eiq-race-v1__matters header span { color: var(--eiq-product-blue) !important; font-size: 12px !important; line-height: 16px !important; font-weight: 700 !important; text-transform: uppercase !important; }
.edgeiq-os .eiq-race-v1__summary-card strong { color: var(--eiq-product-text) !important; font-size: 20px !important; line-height: 24px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__summary-card p { margin: 0 !important; color: var(--eiq-product-muted) !important; font-size: 13px !important; line-height: 18px !important; font-weight: 500 !important; }
.edgeiq-os .eiq-race-v1__matters, .edgeiq-os .eiq-race-v1__conditions, .edgeiq-os .eiq-race-v1__board { padding: 14px !important; }
.edgeiq-os .eiq-race-v1__matters header, .edgeiq-os .eiq-race-v1__speed header, .edgeiq-os .eiq-race-v1__epi header, .edgeiq-os .eiq-race-v1__board header { min-height: 30px !important; display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; }
.edgeiq-os .eiq-race-v1 h2 { margin: 0 !important; color: var(--eiq-product-text) !important; font-size: 15px !important; line-height: 20px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__matters > div { display: grid !important; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)) !important; gap: 8px 14px !important; margin-top: 8px !important; }
.edgeiq-os .eiq-race-v1__matters p { min-height: 28px !important; display: flex !important; align-items: flex-start !important; gap: 8px !important; margin: 0 !important; color: var(--eiq-product-text) !important; font-size: 13px !important; line-height: 18px !important; font-weight: 600 !important; }
.edgeiq-os .eiq-race-v1__matters p span { width: 6px !important; height: 6px !important; flex: 0 0 6px !important; margin-top: 6px !important; border-radius: 999px !important; background: var(--eiq-product-blue) !important; }
.edgeiq-os .eiq-race-v1__midrow { display: grid !important; grid-template-columns: minmax(0, 3fr) minmax(330px, 2fr) !important; gap: 10px !important; }
.edgeiq-os .eiq-race-v1__speed, .edgeiq-os .eiq-race-v1__epi { min-height: 220px !important; padding: 14px !important; }
.edgeiq-os .eiq-race-v1__speed-grid { display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 8px !important; margin-top: 10px !important; }
.edgeiq-os .eiq-race-v1__speed-zone { min-height: 154px !important; display: grid !important; align-content: start !important; gap: 8px !important; padding: 10px !important; border: 1px solid var(--eiq-product-border-soft) !important; border-radius: 8px !important; background: #f8fafc !important; }
.edgeiq-os .eiq-race-v1__speed-zone strong { color: var(--eiq-product-muted) !important; font-size: 12px !important; line-height: 16px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__speed-zone div { display: grid !important; gap: 6px !important; }
.edgeiq-os .eiq-race-v1__speed-zone span { min-height: 28px !important; display: flex !important; align-items: center !important; gap: 6px !important; padding: 0 8px !important; border: 1px solid var(--eiq-product-border) !important; border-radius: 8px !important; background: #ffffff !important; color: var(--eiq-product-text) !important; font-size: 13px !important; font-weight: 700 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
.edgeiq-os .eiq-race-v1__speed-zone b, .edgeiq-os .eiq-race-v1__speed-zone em { color: var(--eiq-product-blue) !important; font-size: 12px !important; font-style: normal !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__speed-zone em { margin-left: auto !important; }
.edgeiq-os .eiq-race-v1__empty { min-height: 162px !important; display: grid !important; place-items: center !important; color: var(--eiq-product-muted) !important; font-size: 13px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__epi > div { display: grid !important; gap: 8px !important; margin-top: 10px !important; }
.edgeiq-os .eiq-race-v1__epi-row { min-height: 50px !important; display: grid !important; grid-template-columns: 34px 42px minmax(0, 1fr) 70px 118px !important; align-items: center !important; gap: 8px !important; padding: 0 10px !important; border: 1px solid var(--eiq-product-border-soft) !important; border-radius: 8px !important; background: #ffffff !important; }
.edgeiq-os .eiq-race-v1__epi-row b, .edgeiq-os .eiq-race-v1__epi-row span, .edgeiq-os .eiq-race-v1__epi-row em, .edgeiq-os .eiq-race-v1__epi-row small { color: var(--eiq-product-text) !important; font-size: 13px !important; font-style: normal !important; font-weight: 700 !important; text-align: center !important; }
.edgeiq-os .eiq-race-v1__epi-row strong { min-width: 0 !important; color: var(--eiq-product-text) !important; font-size: 14px !important; font-weight: 700 !important; text-align: left !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
.edgeiq-os .eiq-race-v1__epi-row small { color: var(--eiq-product-muted) !important; font-size: 12px !important; }
.edgeiq-os .eiq-race-v1__epi-row.is-empty { opacity: 0.72 !important; }
.edgeiq-os .eiq-race-v1__conditions dl { margin: 10px 0 0 !important; display: grid !important; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)) !important; gap: 8px !important; }
.edgeiq-os .eiq-race-v1__conditions dl div { display: grid !important; gap: 2px !important; min-height: 42px !important; align-content: center !important; padding: 8px 10px !important; border: 1px solid var(--eiq-product-border-soft) !important; border-radius: 8px !important; }
.edgeiq-os .eiq-race-v1__conditions dt { color: var(--eiq-product-muted) !important; font-size: 12px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__conditions dd { margin: 0 !important; color: var(--eiq-product-text) !important; font-size: 13px !important; font-weight: 500 !important; }
.edgeiq-os .eiq-race-v1__table-wrap { width: 100% !important; overflow-x: auto !important; margin-top: 10px !important; }
.edgeiq-os .eiq-race-v1__table { min-width: 1238px !important; table-layout: fixed !important; }
.edgeiq-os .eiq-race-v1__table .col-no { width: 48px !important; } .edgeiq-os .eiq-race-v1__table .col-silk { width: 54px !important; } .edgeiq-os .eiq-race-v1__table .col-runner { width: auto !important; min-width: 190px !important; } .edgeiq-os .eiq-race-v1__table .col-bar { width: 54px !important; } .edgeiq-os .eiq-race-v1__table .col-wgt { width: 70px !important; } .edgeiq-os .eiq-race-v1__table .col-jockey { width: 150px !important; } .edgeiq-os .eiq-race-v1__table .col-trainer { width: 170px !important; } .edgeiq-os .eiq-race-v1__table .col-epi { width: 74px !important; } .edgeiq-os .eiq-race-v1__table .col-speed { width: 96px !important; } .edgeiq-os .eiq-race-v1__table .col-edgeiq { width: 104px !important; } .edgeiq-os .eiq-race-v1__table .col-market { width: 86px !important; } .edgeiq-os .eiq-race-v1__table .col-status { width: 104px !important; }
.edgeiq-os .eiq-race-v1__table thead th { height: 42px !important; text-align: center !important; font-size: 13px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__table tbody td { height: 44px !important; text-align: center !important; font-size: 13px !important; font-weight: 500 !important; }
.edgeiq-os .eiq-race-v1__table th.is-left, .edgeiq-os .eiq-race-v1__table td.is-left { text-align: left !important; }
.edgeiq-os .eiq-race-v1__table td strong { color: var(--eiq-product-text) !important; font-size: 14px !important; font-weight: 700 !important; }
.edgeiq-os .eiq-race-v1__silk { width: 32px !important; height: 32px !important; display: inline-block !important; object-fit: contain !important; vertical-align: middle !important; }
.edgeiq-os .eiq-race-v1__silk.is-empty { border: 1px solid var(--eiq-product-border) !important; border-radius: 999px !important; background: #f8fafc !important; }
.edgeiq-os .eiq-race-v1__table tr.is-scratched { opacity: 0.56 !important; }
.edgeiq-os .eiq-race-v1__table tr.is-scratched td:nth-child(3) strong { text-decoration: line-through !important; }
.edgeiq-os .eiq-race-v1__status { min-height: 24px !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; min-width: 74px !important; padding: 0 8px !important; border: 1px solid var(--eiq-product-border) !important; border-radius: 999px !important; background: #f8fafc !important; color: var(--eiq-product-text) !important; font-size: 12px !important; font-weight: 700 !important; }
@media (max-width: 1500px) { .edgeiq-os .eiq-race-v1__metadata { grid-template-columns: repeat(4, minmax(130px, 1fr)) !important; } .edgeiq-os .eiq-race-v1__midrow { grid-template-columns: minmax(0, 3fr) minmax(310px, 2fr) !important; } }
@media (max-width: 1366px) { .edgeiq-os .eiq-race-v1__identity h1, .edgeiq-os .eiq-race-v1__identity h1 span { font-size: 21px !important; line-height: 27px !important; } .edgeiq-os .eiq-race-v1__speed-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; } }
'''


def patch_css() -> None:
    text = CSS.read_text(encoding="utf-8")
    marker = "/* EDGEIQ RACE WORKSPACE V1 LOCKED SPECIFICATION */"
    if marker in text:
        text = text[: text.index(marker)].rstrip()
    CSS.write_text(text.rstrip() + CSS_BLOCK + "\n", encoding="utf-8")


def main() -> None:
    patch_presentation()
    patch_racefile_routing()
    patch_race_workspace()
    write_view_model()
    write_race_intelligence()
    patch_css()
    print("Applied EDGEIQ Race Workspace V1 locked specification.")


if __name__ == "__main__":
    main()
