from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / 'src' / 'edgeiq-os' / 'race' / 'components' / 'RaceFormGuideWorkspace.tsx'
REPORT = ROOT / 'docs' / 'product-specification' / 'FORM_GUIDE_FINAL_TABLE_APPLY_V2.json'

COMPONENT = r'''import { Fragment, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import {
  displayOrDash,
  normaliseFormGuideRace,
  type FormGuideRunnerDisplay,
  type FormGuideProfileLine,
} from "../services/formGuideNormaliser";
import {
  findEnrichedFormGuideRace,
  loadFormGuideEnrichedFeed,
  type EnrichedFormGuideRace,
} from "../services/formGuideEnrichedFeed";
import { buildRunnerProfileDossier } from "../services/formGuideWorkspaceViewModel";

type RaceFormGuideWorkspaceProps = {
  raceBook: any;
  field: ThreeDayRunner[];
  meetingRaces: ThreeDayRace[];
  selectedRaceKey?: string;
  onOpenRace?: (race: ThreeDayRace) => void;
};

const DASH = "—";

const metricDefinitions = {
  "LAST 5": "Five most recent official finish positions.",
  DAYS: "Days since the runner's latest official race start.",
  EPI: "EDGEiQ Performance Index for the selected race context.",
  "EARLY SPEED": "Projected early-position strength.",
  "LATE SPEED": "Late-speed or finish-strength projection.",
  SUITABILITY: "Current race fit across distance, conditions, class and setup.",
  "FORM MOMENTUM": "Recent performance trend from governed FORM evidence.",
  MARKET: "Current market display price where available.",
  "EDGEiQ PRICE": "EDGEiQ display price from the approved price feed; maths unchanged.",
} as const;

const summaryColumns = [
  "NO",
  "SILK",
  "LAST 5",
  "HORSE",
  "TRAINER",
  "JOCKEY",
  "WT",
  "BAR",
  "DAYS",
  "EPI",
  "EARLY SPEED",
  "LATE SPEED",
  "SUITABILITY",
  "FORM MOMENTUM",
  "MARKET",
  "EDGEiQ PRICE",
] as const;

const summaryColumnWidths = [
  "38px",
  "46px",
  "86px",
  "170px",
  "138px",
  "132px",
  "48px",
  "42px",
  "48px",
  "58px",
  "78px",
  "76px",
  "90px",
  "104px",
  "72px",
  "88px",
];

const recentFormColumns = [
  "DATE",
  "TRACK",
  "DIST",
  "CLASS",
  "GOING",
  "JOCKEY",
  "BARRIER",
  "WEIGHT",
  "EPI",
  "ERI",
  "POS",
  "POSITION IN RUNNING",
  "MARGIN",
  "SP",
  "8-6",
  "6-4",
  "4-2",
  "2-F",
] as const;

type TooltipState = { column: string; definition: string; left: number; top: number } | null;
type ProfileMetricKey = "starts" | "wins" | "places" | "winPct" | "placePct" | "avgEpi" | "avgEri";
type ProfileMatrixColumn = { key: string; label: string; today: boolean; primary: boolean; source: FormGuideProfileLine | null };

function cleanDisplay(value: string | number | null | undefined): string {
  const text = String(value ?? "").trim();
  if (!text || ["UNKNOWN", "NOT LOADED", "SOURCE GAP", "NULL", "UNDEFINED", "NAN"].includes(text.toUpperCase())) return DASH;
  if (text === "0.0%") return DASH;
  return text;
}

function safeAnchorPart(value: string): string {
  return String(value || "").trim().replace(/[^a-z0-9_-]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase();
}

function runnerProfileId(runner: FormGuideRunnerDisplay): string {
  return `runner-profile-${safeAnchorPart(runner.id)}`;
}

function clamp(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function parsePriceValue(value: string): number | null {
  const text = String(value || "").replace(/[$,]/g, "").trim();
  if (!text) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function percentText(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function runnerValueDeltaDisplay(runner: FormGuideRunnerDisplay): string {
  const market = parsePriceValue(runner.marketPrice);
  const edgeiq = parsePriceValue(runner.edgeiqPrice);
  if (market === null || edgeiq === null || edgeiq === 0) return "";
  return percentText(((market - edgeiq) / edgeiq) * 100);
}

function scrollToRunner(runner: FormGuideRunnerDisplay) {
  const element = document.getElementById(runnerProfileId(runner));
  if (!element) return;
  const top = element.getBoundingClientRect().top + window.scrollY - 16;
  window.scrollTo({ top, behavior: "smooth" });
  window.history.replaceState(null, "", `#${runnerProfileId(runner)}`);
}

function MetricHeader({ column, setActiveTooltip }: { column: (typeof summaryColumns)[number]; setActiveTooltip: (state: TooltipState) => void }) {
  const definition = metricDefinitions[column as keyof typeof metricDefinitions];
  const showTooltip = (target: HTMLElement) => {
    if (!definition) return;
    const rect = target.getBoundingClientRect();
    const width = 292;
    const left = clamp(rect.left + rect.width / 2, width / 2 + 12, window.innerWidth - width / 2 - 12);
    const top = rect.top - 16 < 12 ? 12 : rect.top - 16;
    setActiveTooltip({ column, definition, left, top });
  };

  if (!definition) return <span>{column}</span>;
  return (
    <button
      type="button"
      className="eiq-form-tooltip-trigger"
      aria-label={`${column}: ${definition}`}
      onMouseEnter={(event) => showTooltip(event.currentTarget)}
      onClick={(event) => showTooltip(event.currentTarget)}
      onMouseLeave={() => setActiveTooltip(null)}
      onFocus={(event) => showTooltip(event.currentTarget)}
      onBlur={() => setActiveTooltip(null)}
    >
      {column}
    </button>
  );
}

function LastFiveStrip({ values }: { values: string[] }) {
  return (
    <span className="eiq-form-last5-strip" aria-label="Last five starts">
      {values.slice(0, 5).map((value, index) => (
        <span key={`${value}-${index}`}>{cleanDisplay(value)}</span>
      ))}
    </span>
  );
}

function CurrentMetricStrip({ runner }: { runner: FormGuideRunnerDisplay }) {
  const metrics = [
    ["Current EPI", runner.epi, runner.epiDifference],
    ["ERI", runner.rating, runner.epiRank ? `Rank ${runner.epiRank}` : ""],
    ["Suitability", runner.suitabilityScore, runner.suitabilityLabel],
    ["Form Momentum", runner.formMomentum, runner.formMomentumDirection === "up" ? "Rising" : runner.formMomentumDirection === "down" ? "Easing" : ""],
    ["Market", runner.marketPrice, runnerValueDeltaDisplay(runner) ? `Edge ${runnerValueDeltaDisplay(runner)}` : ""],
    ["EDGEiQ Price", runner.edgeiqPrice, ""],
  ];

  return (
    <dl className="eiq-form-v4-current-strip eiq-form-final-current-strip" data-region="hero_metrics">
      {metrics.map(([label, value, sublabel]) => (
        <div key={label} className={value ? "" : "is-empty"}>
          <dt>{label}</dt>
          <dd>{cleanDisplay(value)}</dd>
          {sublabel ? <small>{cleanDisplay(sublabel)}</small> : null}
        </div>
      ))}
    </dl>
  );
}

function profileLineByLabel(rows: FormGuideProfileLine[], labels: string[]): FormGuideProfileLine | null {
  const keys = labels.map((value) => value.toUpperCase().replace(/[^A-Z0-9]+/g, ""));
  return rows.find((row) => keys.includes(row.label.toUpperCase().replace(/[^A-Z0-9]+/g, ""))) ?? null;
}

function bestProfileLine(rows: FormGuideProfileLine[]): FormGuideProfileLine | null {
  return rows.find((row) => row.matchesToday && row.record) ?? rows.find((row) => row.record) ?? null;
}

function placesFromLine(line: FormGuideProfileLine | null): string {
  if (!line) return "";
  const seconds = Number(line.seconds);
  const thirds = Number(line.thirds);
  if (!Number.isFinite(seconds) && !Number.isFinite(thirds)) return "";
  return String((Number.isFinite(seconds) ? seconds : 0) + (Number.isFinite(thirds) ? thirds : 0));
}

function profileMetricValue(column: ProfileMatrixColumn, metric: ProfileMetricKey, runner: FormGuideRunnerDisplay): string {
  const line = column.source;
  if (!line) return "";
  if (metric === "starts") return line.starts;
  if (metric === "wins") return line.wins;
  if (metric === "places") return placesFromLine(line);
  if (metric === "winPct") return line.winPct;
  if (metric === "placePct") return line.placePct;
  if (metric === "avgEpi") return column.key === "career" ? runner.epi : "";
  if (metric === "avgEri") return column.key === "career" ? runner.rating : "";
  return "";
}

function HorseProfileMatrix({ runner }: { runner: FormGuideRunnerDisplay }) {
  const career = profileLineByLabel(runner.careerProfile, ["Career"]);
  const distance = profileLineByLabel(runner.careerProfile, ["Distance"]);
  const track = profileLineByLabel(runner.careerProfile, ["Track"]);
  const trackDistance = profileLineByLabel(runner.careerProfile, ["Track/Dist", "Track Distance"]);
  const firm = profileLineByLabel(runner.conditionProfile, ["Firm"]);
  const todayGoing = runner.conditionProfile.find((row) => row.matchesToday) ?? profileLineByLabel(runner.conditionProfile, ["Good"]);
  const soft = profileLineByLabel(runner.conditionProfile, ["Soft"]);
  const heavy = profileLineByLabel(runner.conditionProfile, ["Heavy"]);
  const todayClass = bestProfileLine(runner.classProfile);
  const jockey = profileLineByLabel(runner.jockeyProfile, ["Current Jockey", "Jockey"]);
  const firstUp = profileLineByLabel(runner.raceDayPattern, ["1st Up", "First Up"]);
  const secondUp = profileLineByLabel(runner.raceDayPattern, ["2nd Up", "Second Up"]);
  const thirdUp = profileLineByLabel(runner.raceDayPattern, ["3rd Up", "Third Up"]);
  const columns: ProfileMatrixColumn[] = [
    { key: "career", label: "CAREER", today: false, primary: false, source: career },
    { key: "today_distance", label: "TODAY DISTANCE", today: Boolean(distance?.matchesToday || distance?.record), primary: false, source: distance },
    { key: "today_track", label: "TODAY TRACK", today: Boolean(track?.matchesToday || track?.record), primary: false, source: track },
    { key: "firm", label: "FIRM", today: false, primary: false, source: firm },
    { key: "today_going", label: "TODAY GOING", today: Boolean(todayGoing?.matchesToday || todayGoing?.record), primary: true, source: todayGoing },
    { key: "soft", label: "SOFT", today: false, primary: false, source: soft },
    { key: "heavy", label: "HEAVY", today: false, primary: false, source: heavy },
    { key: "track_dist", label: "TRACK/DIST", today: Boolean(trackDistance?.matchesToday || trackDistance?.record), primary: false, source: trackDistance },
    { key: "today_class", label: "TODAY CLASS", today: Boolean(todayClass?.matchesToday || todayClass?.record), primary: false, source: todayClass },
    { key: "today_jockey", label: "TODAY JOCKEY", today: Boolean(jockey?.matchesToday || jockey?.record), primary: false, source: jockey },
    { key: "first_up", label: "1ST UP", today: false, primary: false, source: firstUp },
    { key: "second_up", label: "2ND UP", today: false, primary: false, source: secondUp },
    { key: "third_up", label: "3RD UP", today: false, primary: false, source: thirdUp },
  ];
  const rows: Array<[ProfileMetricKey, string]> = [["starts", "STARTS"], ["wins", "WINS"], ["places", "PLACES"], ["winPct", "WIN %"], ["placePct", "PLACE %"], ["avgEpi", "AVG EPI"], ["avgEri", "AVG ERI"]];

  return (
    <section className="eiq-form-final-profile-matrix" data-region="profile_matrix">
      <header><span>HORSE PROFILE (CAREER)</span></header>
      <div className="eiq-form-final-profile-grid" role="table" aria-label="Horse Profile Career Matrix">
        <div className="eiq-form-final-profile-cell eiq-form-final-profile-cell--head">CATEGORY</div>
        {columns.map((column) => (
          <div key={column.key} className={`eiq-form-final-profile-cell eiq-form-final-profile-cell--head ${column.today ? "is-today" : ""} ${column.primary ? "is-primary" : ""}`.trim()}>
            {column.today ? <em>TODAY</em> : null}
            <strong>{column.label}</strong>
          </div>
        ))}
        {rows.map(([metric, label]) => (
          <Fragment key={metric}>
            <div className="eiq-form-final-profile-cell eiq-form-final-profile-cell--rowhead">{label}</div>
            {columns.map((column) => (
              <div key={`${metric}-${column.key}`} className={`eiq-form-final-profile-cell ${column.today ? "is-today" : ""} ${column.primary ? "is-primary" : ""}`.trim()}>{cleanDisplay(profileMetricValue(column, metric, runner))}</div>
            ))}
          </Fragment>
        ))}
      </div>
    </section>
  );
}

function TodayMatch({ runner }: { runner: FormGuideRunnerDisplay }) {
  const track = profileLineByLabel(runner.careerProfile, ["Track"]);
  const distance = profileLineByLabel(runner.careerProfile, ["Distance"]);
  const going = runner.conditionProfile.find((row) => row.matchesToday) ?? null;
  const classMatch = bestProfileLine(runner.classProfile);
  const rows = [
    { label: "Track", value: track?.record ? "Current Track" : "", assessment: track?.record ? track.record : "" },
    { label: "Distance", value: distance?.record ? "Today Distance" : "", assessment: distance?.record ? distance.record : "" },
    { label: "Going", value: going?.label || "", assessment: going?.record || "" },
    { label: "Rail", value: "", assessment: "" },
    { label: "Tempo", value: runner.shapeFit || "", assessment: runner.shapeFit ? "Governed read" : "" },
    { label: "Pace Setup", value: runner.earlySpeed || runner.late || "", assessment: runner.earlySpeed || runner.late ? "Projected read" : "" },
  ];
  return (
    <aside className="eiq-form-v4-today-match eiq-form-final-today-match" data-region="today_match">
      <h3>TODAY'S MATCH</h3>
      <ul>
        {rows.map((item) => (
          <li key={item.label}>
            <i aria-hidden="true" />
            <strong>{item.label}</strong>
            <span>{cleanDisplay(item.value)}</span>
            <small>{cleanDisplay(item.assessment)}</small>
          </li>
        ))}
      </ul>
      <div className="eiq-form-final-match-rating">
        <span>Overall Match Rating</span>
        <strong>{cleanDisplay(runner.suitabilityScore)}</strong>
        <small>{cleanDisplay(runner.suitabilityLabel || classMatch?.label)}</small>
      </div>
    </aside>
  );
}

function KeyInsights({ runner }: { runner: FormGuideRunnerDisplay }) {
  const dossier = buildRunnerProfileDossier(runner);
  const groups = dossier.keyInsights;
  const firstItems = groups.flatMap((group) => group.items.map((item) => item.text)).filter(Boolean).slice(0, 4);

  return (
    <section className="eiq-form-v31-insights eiq-form-v4-key-insights eiq-form-final-match-read" data-region="match_insights">
      <h3>MATCH READ</h3>
      {firstItems.length ? (
        <ul>
          {firstItems.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : (
        <p>{runner.scratched ? "Runner is scratched. Historical evidence remains below." : "No governed match read available for this runner."}</p>
      )}
    </section>
  );
}

function sectionalClassName(value: string): string {
  const parsed = Number(String(value || "").replace("+", ""));
  if (!Number.isFinite(parsed)) return "is-empty";
  if (parsed < 0) return "is-negative";
  if (parsed > 0) return "is-positive";
  return "is-neutral";
}

function goingClassName(value: string): string {
  const condition = value.toUpperCase();
  if (condition.includes("HEAVY")) return "is-heavy";
  if (condition.includes("SOFT")) return "is-soft";
  if (condition.includes("GOOD")) return "is-good";
  if (condition.includes("FIRM")) return "is-firm";
  return "";
}

function RecentForm({ runner }: { runner: FormGuideRunnerDisplay }) {
  return (
    <section className="eiq-form-v31-recent-form eiq-form-v4-recent-form eiq-form-final-recent-form" data-region="recent_form">
      <header>
        <div>
          <span>RECENT FORM</span>
          <strong>LAST 8 STARTS</strong>
        </div>
      </header>
      <div className="eiq-form-run-table eiq-form-run-table--v3 eiq-form-run-table--v4">
        <table data-columns={recentFormColumns.join("|")}>
          <thead><tr>{recentFormColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>
            {runner.recentRuns.map((run, index) => (
              <tr key={`${runner.id}-run-${index}`}>
                <td>{cleanDisplay(run.date)}</td>
                <td>{cleanDisplay(run.track)}</td>
                <td>{cleanDisplay(run.distance)}</td>
                <td>{cleanDisplay(run.raceClass)}</td>
                <td className={`eiq-going-cell ${goingClassName(run.condition)}`.trim()}>{cleanDisplay(run.condition)}</td>
                <td>{cleanDisplay(run.jockey)}</td>
                <td>{cleanDisplay(run.barrier)}</td>
                <td>{cleanDisplay(run.weight)}</td>
                <td>{cleanDisplay(run.epi)}</td>
                <td>{cleanDisplay(run.eri)}</td>
                <td>{cleanDisplay(run.position)}</td>
                <td>{cleanDisplay(run.positionInRunning)}</td>
                <td>{cleanDisplay(run.margin)}</td>
                <td>{cleanDisplay(run.sp)}</td>
                <td className={sectionalClassName(run.esi800600)}>{cleanDisplay(run.esi800600)}</td>
                <td className={sectionalClassName(run.esi600400)}>{cleanDisplay(run.esi600400)}</td>
                <td className={sectionalClassName(run.esi400200)}>{cleanDisplay(run.esi400200)}</td>
                <td className={sectionalClassName(run.esi200F)}>{cleanDisplay(run.esi200F)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!runner.recentRuns.length ? <p className="eiq-form-empty">No governed recent-form rows available.</p> : null}
    </section>
  );
}

function RunnerProfile({ runner }: { runner: FormGuideRunnerDisplay }) {
  const identity = [
    runner.age ? `${runner.age}yo` : "",
    runner.sex,
    runner.breeding,
    runner.trainer ? `Trainer: ${runner.trainer}` : "",
    runner.jockey ? `Jockey: ${runner.jockey}` : "",
    runner.effectiveBarrier ? `Eff Bar ${runner.effectiveBarrier}` : runner.barrier ? `Bar ${runner.barrier}` : "",
    runner.weight,
  ].filter(Boolean);

  return (
    <article id={runnerProfileId(runner)} className={`eiq-form-v31-runner-sheet eiq-form-v4-runner-sheet eiq-form-final-runner-sheet ${runner.scratched ? "is-scratched" : ""}`.trim()} data-runner-profile="true" data-runner-no={runner.no}>
      <section className="eiq-form-v3-runner-header eiq-form-v31-runner-header eiq-form-v4-runner-header eiq-form-final-runner-header" data-region="runner_header">
        {runner.silkUrl ? <img className="eiq-form-detail-silk" src={runner.silkUrl} alt={`${runner.horse} silks`} loading="lazy" /> : <span className="eiq-form-detail-silk eiq-form-silk--fallback" aria-hidden="true" />}
        <div className="eiq-form-v3-runner-identity">
          <span>{runner.scratched ? "SCRATCHED RUNNER" : "HORSE PROFILE"}</span>
          <strong><em>{runner.no}</em>{runner.horse}</strong>
          <p>{identity.length ? identity.join(" | ") : DASH}</p>
        </div>
        <CurrentMetricStrip runner={runner} />
      </section>

      <section className="eiq-form-v4-dossier-grid eiq-form-approved-dossier-grid eiq-form-final-dossier-grid" data-region="expanded_runner">
        <TodayMatch runner={runner} />
        <div className="eiq-form-v4-dossier-main eiq-form-final-dossier-main" data-region="profile_matrix_wrap">
          <HorseProfileMatrix runner={runner} />
        </div>
        <KeyInsights runner={runner} />
      </section>

      <RecentForm runner={runner} />
      <div className="eiq-form-final-sectional-legend" data-region="sectional_legend"><strong>Sectionals (Lengths):</strong><span>Negative = faster than standard</span><span>Positive = slower than standard</span></div>
    </article>
  );
}

export function RaceFormGuideWorkspace({ raceBook, field, meetingRaces, selectedRaceKey }: RaceFormGuideWorkspaceProps) {
  const [enrichedRace, setEnrichedRace] = useState<EnrichedFormGuideRace | null>(null);
  const [activeTooltip, setActiveTooltip] = useState<TooltipState>(null);
  const [expandedRunnerId, setExpandedRunnerId] = useState<string | null>(null);
  const guide = useMemo(() => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace), [raceBook, field, meetingRaces, enrichedRace]);
  const runnerIds = useMemo(() => guide.runners.map((runner) => runner.id).join("|"), [guide.runners]);

  useEffect(() => {
    if (!guide.runners.length) {
      if (expandedRunnerId !== null) setExpandedRunnerId(null);
      return;
    }
    const withHistory = guide.runners.find((runner) => runner.recentRuns.length >= 3 && !runner.scratched);
    const fallback = guide.runners.find((runner) => !runner.scratched) ?? guide.runners[0];
    const preferred = withHistory ?? fallback;
    if (!expandedRunnerId || !guide.runners.some((runner) => runner.id === expandedRunnerId)) {
      setExpandedRunnerId(preferred.id);
    }
  }, [expandedRunnerId, guide.runners, runnerIds]);

  useEffect(() => {
    let cancelled = false;
    loadFormGuideEnrichedFeed()
      .then((feed) => {
        if (cancelled) return;
        setEnrichedRace(findEnrichedFormGuideRace(feed, raceBook, meetingRaces));
      })
      .catch((error) => {
        console.warn("Form Guide enrichment unavailable", error);
        if (!cancelled) setEnrichedRace(null);
      });
    return () => { cancelled = true; };
  }, [raceBook, meetingRaces, selectedRaceKey]);

  return (
    <section className="eiq-race-form-guide eiq-race-form-guide--v3 eiq-race-form-guide--v4 eiq-race-form-guide--all-runner eiq-race-form-guide--approved-exact eiq-race-form-guide--final-locked" aria-label="Race form guide" data-edgeiq-workspace="form-guide-final-locked" data-region="form_guide_workspace">
      <header className="eiq-form-race-header eiq-form-race-header--v3">
        <div className="eiq-form-v3-race-title">
          <span>FORM GUIDE</span>
          <strong>{cleanDisplay(guide.primaryLine)}</strong>
          <h2>{cleanDisplay(guide.raceName)}</h2>
        </div>
        {guide.metadata.length ? <dl>{guide.metadata.map((item) => <div key={`${item.label}-${item.value}`}><dt>{item.label}</dt><dd>{cleanDisplay(item.value)}</dd></div>)}</dl> : null}
      </header>

      <div className="eiq-form-approved-tools eiq-form-final-tools" data-region="form_tools" aria-label="Form guide controls">
        <label><span>Ratings View</span><select defaultValue="EPI" aria-label="Ratings View"><option>EPI</option><option>ERI</option></select></label>
        <button type="button" aria-label="Metric information">i</button>
        <button type="button">CUSTOMISE COLUMNS</button>
        <button type="button">EXPORT</button>
      </div>

      <div className="eiq-form-summary-table eiq-form-summary-table--v3 eiq-form-summary-table--all-runner eiq-form-summary-table--final-locked" data-region="summary_table" data-columns={summaryColumns.join("|")}>
        <table>
          <colgroup>{summaryColumnWidths.map((width, index) => <col key={`${summaryColumns[index]}-${width}`} style={{ width }} />)}</colgroup>
          <thead><tr>{summaryColumns.map((column) => <th key={column}><MetricHeader column={column} setActiveTooltip={setActiveTooltip} /></th>)}</tr></thead>
          <tbody>
            {guide.runners.map((runner) => {
              const isExpanded = expandedRunnerId === runner.id;
              return (
                <Fragment key={runner.id}>
                  <tr className={`${runner.scratched ? "is-scratched" : ""} ${isExpanded ? "is-expanded" : ""}`.trim()}>
                    <td className="eiq-cell-no">{cleanDisplay(runner.no)}</td>
                    <td>{runner.silkUrl ? <img className="eiq-form-silk" src={runner.silkUrl} alt={`${runner.horse} silks`} loading="lazy" /> : <span className="eiq-form-silk eiq-form-silk--fallback" aria-hidden="true" />}</td>
                    <td className="eiq-cell-last-five">{runner.lastFive.length ? <LastFiveStrip values={runner.lastFive} /> : DASH}</td>
                    <td><button type="button" className="eiq-form-runner-anchor eiq-form-runner-expand" aria-expanded={isExpanded} aria-controls={runnerProfileId(runner)} onClick={() => { const next = isExpanded ? null : runner.id; setExpandedRunnerId(next); if (!isExpanded) window.requestAnimationFrame(() => scrollToRunner(runner)); }}><strong>{cleanDisplay(runner.horse)}</strong>{runner.scratched ? <small>SCRATCHED</small> : null}</button></td>
                    <td>{cleanDisplay(runner.trainer)}</td>
                    <td>{cleanDisplay(runner.jockey)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.weight)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.barrier)}</td>
                    <td className="eiq-cell-days">{cleanDisplay(runner.daysSinceLastRun)}</td>
                    <td className="eiq-cell-epi">{cleanDisplay(runner.epi)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.earlySpeed)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.late)}</td>
                    <td className="eiq-cell-suitability"><strong>{cleanDisplay(runner.suitabilityScore)}</strong><small>{cleanDisplay(runner.suitabilityLabel)}</small></td>
                    <td className="eiq-cell-momentum" data-direction={runner.formMomentumDirection}>{cleanDisplay(runner.formMomentum)}</td>
                    <td className="eiq-cell-price eiq-cell-market">{cleanDisplay(runner.marketPrice)}</td>
                    <td className="eiq-cell-price eiq-cell-edgeiq-price">{cleanDisplay(runner.edgeiqPrice)}</td>
                  </tr>
                  {isExpanded ? <tr className="eiq-form-expanded-row"><td colSpan={summaryColumns.length}><RunnerProfile runner={runner} /></td></tr> : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <footer className="eiq-form-v3-footer"><span>{cleanDisplay(guide.fieldSummary)}</span><span>Data is modelled and subject to change.</span></footer>
      {activeTooltip ? createPortal(<div className="eiq-form-header-tooltip" role="tooltip" style={{ left: activeTooltip.left, top: activeTooltip.top }} data-column={activeTooltip.column}><strong>{activeTooltip.column}</strong><span>{activeTooltip.definition}</span></div>, document.body) : null}
    </section>
  );
}
'''

def main():
    TSX.write_text(COMPONENT, encoding='utf-8')
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({'status':'FORM_GUIDE_FINAL_TABLE_V2_APPLIED','timestamp':datetime.now().isoformat(timespec='seconds'),'component':str(TSX.relative_to(ROOT))}, indent=2), encoding='utf-8')
    print('FORM_GUIDE_FINAL_TABLE_V2_APPLIED')

if __name__ == '__main__':
    main()
