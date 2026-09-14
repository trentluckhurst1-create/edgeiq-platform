import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { loadRunnerDetail } from "../services/runnerDetailFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";

type PerformanceWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

type RunnerLoad = { runner: ThreeDayRunner | null; loading: boolean; error: string };
type PerformanceIntel = {
  historyCount: number;
  ratedCount: number;
  latestRating: string;
  latestRatingValue: number | null;
  peakRating: string;
  peakRatingValue: number | null;
  ratingTrend: string;
  ratingTrendTone: "up" | "down" | "stable" | "limited";
  ratingTrendDeltaValue: number | null;
  recentForm: string;
  recency: string;
  recencyDays: number | null;
  distanceEvidence: string;
  distanceRunCount: number;
  distanceBestFinish: number | null;
  ratingCoverage: string;
};
type ComparisonRunner = { index: number; runner: ThreeDayRunner; intel: PerformanceIntel };
type ComparisonFilter = "all" | "improvers" | "distance" | "fullyRated" | "limited";
type ComparisonSort = "latest" | "peak" | "trajectory" | "recency" | "distance" | "evidence" | "runner";
type SortDirection = "asc" | "desc";

const FILTERS: { key: ComparisonFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "improvers", label: "Improvers" },
  { key: "distance", label: "Distance Proven" },
  { key: "fullyRated", label: "Fully Rated" },
  { key: "limited", label: "Limited Data" },
];

function display(value: unknown, fallback = "-"): string { return cleanProductText(value, fallback); }
function officialNumber(runner: ThreeDayRunner): string { return display(runner.official.no ?? runner.official.number); }
function runnerName(runner: ThreeDayRunner): string { return display(runner.official.runner, "Unnamed runner"); }
function raceTitle(race: ThreeDayRace): string { return display(race.raceName, `Race ${race.raceNumber}`); }
function detailPath(runner: ThreeDayRunner): string { const value = runner.source?.runnerDetailPath; return typeof value === "string" ? value : ""; }
function asRecord(value: unknown): Record<string, unknown> { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function first(record: Record<string, unknown>, keys: string[], fallback = "-"): string { for (const key of keys) { const value = String(record[key] ?? "").trim(); if (value && value !== "-") return value; } return fallback; }
function historyRows(runner: ThreeDayRunner | null): unknown[] { if (!runner) return []; return Array.isArray(runner.historicalRuns) && runner.historicalRuns.length ? runner.historicalRuns : Array.isArray(runner.evidenceRuns) ? runner.evidenceRuns : []; }
function recentRuns(runner: ThreeDayRunner | null): unknown[] { return historyRows(runner).slice(0, 5); }
function sectionalSummary(runner: ThreeDayRunner | null): Record<string, unknown> { const source = asRecord(runner?.source); return asRecord(source.performanceSectionalSummary); }
function summaryValue(summary: Record<string, unknown>, key: string, fallback = "LIMITED DATA"): string { return display(summary[key], fallback); }

function numeric(value: unknown): number | null {
  const match = String(value ?? "").replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function distanceMetres(value: unknown): number | null {
  const raw = String(value ?? "").trim().toLowerCase();
  const parsed = numeric(raw);
  if (parsed === null) return null;
  return raw.includes("km") ? Math.round(parsed * 1000) : Math.round(parsed);
}

function finishPosition(record: Record<string, unknown>): number | null {
  return numeric(first(record, ["finish", "position", "placing", "place"], ""));
}

function performanceIntel(runner: ThreeDayRunner | null, race: ThreeDayRace, meetingDate: string): PerformanceIntel {
  const rows = historyRows(runner).slice(0, 5).map(asRecord);
  const ratings = rows
    .map((record) => numeric(first(record, ["rating", "wfa", "form_rating", "performance_rating", "figure"], "")))
    .filter((value): value is number => value !== null);
  const latestRatingValue = ratings[0] ?? null;
  const peakRatingValue = ratings.length ? Math.max(...ratings) : null;

  let ratingTrend = "LIMITED DATA";
  let ratingTrendTone: PerformanceIntel["ratingTrendTone"] = "limited";
  let ratingTrendDeltaValue: number | null = null;
  if (ratings.length >= 2) {
    const prior = ratings.slice(1);
    const priorAverage = prior.reduce((sum, value) => sum + value, 0) / prior.length;
    const delta = latestRatingValue! - priorAverage;
    ratingTrendDeltaValue = delta;
    if (delta >= 2) { ratingTrend = `UP +${delta.toFixed(1)}`; ratingTrendTone = "up"; }
    else if (delta <= -2) { ratingTrend = `DOWN ${delta.toFixed(1)}`; ratingTrendTone = "down"; }
    else { ratingTrend = `STABLE ${delta >= 0 ? "+" : ""}${delta.toFixed(1)}`; ratingTrendTone = "stable"; }
  }

  const form = rows.map((record) => first(record, ["finish", "position", "placing", "place"], "")).filter(Boolean).join("-");

  let recency = "LIMITED DATA";
  let recencyDays: number | null = null;
  const latestDateRaw = rows.length ? first(rows[0], ["date", "race_date", "meeting_date", "raceDate"], "") : "";
  const currentDate = Date.parse(meetingDate);
  const latestDate = Date.parse(latestDateRaw);
  if (Number.isFinite(currentDate) && Number.isFinite(latestDate) && currentDate > latestDate) {
    recencyDays = Math.round((currentDate - latestDate) / 86400000);
    recency = `${recencyDays}D`;
  }

  const targetDistance = distanceMetres(race.distance);
  const distanceRows = targetDistance === null ? [] : rows.filter((record) => distanceMetres(first(record, ["distance", "dist", "race_distance"], "")) === targetDistance);
  const distanceFinishes = distanceRows.map(finishPosition).filter((value): value is number => value !== null);
  const distanceBestFinish = distanceFinishes.length ? Math.min(...distanceFinishes) : null;
  let distanceEvidence = "NO MATCHING RUNS";
  if (distanceRows.length) distanceEvidence = distanceBestFinish === null ? `${distanceRows.length} RUN${distanceRows.length === 1 ? "" : "S"}` : `${distanceRows.length} RUN${distanceRows.length === 1 ? "" : "S"} · BEST ${distanceBestFinish}`;

  return {
    historyCount: rows.length,
    ratedCount: ratings.length,
    latestRating: latestRatingValue === null ? "LIMITED DATA" : latestRatingValue.toFixed(1),
    latestRatingValue,
    peakRating: peakRatingValue === null ? "LIMITED DATA" : peakRatingValue.toFixed(1),
    peakRatingValue,
    ratingTrend,
    ratingTrendTone,
    ratingTrendDeltaValue,
    recentForm: form || "LIMITED DATA",
    recency,
    recencyDays,
    distanceEvidence,
    distanceRunCount: distanceRows.length,
    distanceBestFinish,
    ratingCoverage: rows.length ? `${ratings.length}/${rows.length} RATED` : "NO HISTORY",
  };
}

function comparisonName(row: ComparisonRunner | null): string {
  if (!row) return "NO EVIDENCE";
  return `#${officialNumber(row.runner)} ${runnerName(row.runner)}`;
}

function isLimited(row: ComparisonRunner): boolean { return row.intel.historyCount < 2 || row.intel.ratedCount < 1; }
function isFullyRated(row: ComparisonRunner): boolean { return row.intel.historyCount >= 2 && row.intel.ratedCount === row.intel.historyCount; }
function filterComparison(row: ComparisonRunner, filter: ComparisonFilter): boolean {
  if (filter === "improvers") return (row.intel.ratingTrendDeltaValue ?? 0) > 0;
  if (filter === "distance") return row.intel.distanceRunCount > 0;
  if (filter === "fullyRated") return isFullyRated(row);
  if (filter === "limited") return isLimited(row);
  return true;
}

function sortValue(row: ComparisonRunner, sort: ComparisonSort): number | string | null {
  if (sort === "latest") return row.intel.latestRatingValue;
  if (sort === "peak") return row.intel.peakRatingValue;
  if (sort === "trajectory") return row.intel.ratingTrendDeltaValue;
  if (sort === "recency") return row.intel.recencyDays;
  if (sort === "distance") return row.intel.distanceRunCount;
  if (sort === "evidence") return row.intel.historyCount ? row.intel.ratedCount / row.intel.historyCount : null;
  return runnerName(row.runner).toUpperCase();
}

function compareRows(a: ComparisonRunner, b: ComparisonRunner, sort: ComparisonSort, direction: SortDirection): number {
  const av = sortValue(a, sort);
  const bv = sortValue(b, sort);
  if (av === null && bv === null) return a.index - b.index;
  if (av === null) return 1;
  if (bv === null) return -1;
  let result = 0;
  if (typeof av === "string" && typeof bv === "string") result = av.localeCompare(bv);
  else result = Number(av) - Number(bv);
  if (sort === "recency") result *= -1;
  return direction === "asc" ? result : -result;
}

export function PerformanceWorkspace({ meeting, selectedRaceKey, onRaceChange }: PerformanceWorkspaceProps) {
  const selectedRace = useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);

  const [selectedRunnerIndex, setSelectedRunnerIndex] = useState(0);
  const [detail, setDetail] = useState<RunnerLoad>({ runner: null, loading: false, error: "" });
  const [comparisonDetails, setComparisonDetails] = useState<Record<number, ThreeDayRunner>>({});
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonFilter, setComparisonFilter] = useState<ComparisonFilter>("all");
  const [comparisonSort, setComparisonSort] = useState<ComparisonSort>("latest");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  useEffect(() => {
    setSelectedRunnerIndex(0);
    setComparisonFilter("all");
    setComparisonSort("latest");
    setSortDirection("desc");
  }, [selectedRace?.raceKey]);

  const selectedRunner = selectedRace?.runners[selectedRunnerIndex] ?? null;

  useEffect(() => {
    let active = true;
    if (!selectedRunner) {
      setDetail({ runner: null, loading: false, error: "" });
      return () => { active = false; };
    }
    const path = detailPath(selectedRunner);
    if (!path) {
      setDetail({ runner: selectedRunner, loading: false, error: "" });
      return () => { active = false; };
    }
    setDetail({ runner: selectedRunner, loading: true, error: "" });
    loadRunnerDetail(path)
      .then((runner) => { if (active) setDetail({ runner, loading: false, error: "" }); })
      .catch((error) => { if (active) setDetail({ runner: selectedRunner, loading: false, error: error instanceof Error ? error.message : "Performance detail unavailable" }); });
    return () => { active = false; };
  }, [selectedRunner]);

  useEffect(() => {
    let active = true;
    if (!selectedRace) {
      setComparisonDetails({});
      setComparisonLoading(false);
      return () => { active = false; };
    }
    setComparisonDetails({});
    setComparisonLoading(true);
    const jobs = selectedRace.runners.map(async (runner, index) => {
      const path = detailPath(runner);
      if (!path) return [index, runner] as const;
      try { return [index, await loadRunnerDetail(path)] as const; }
      catch { return [index, runner] as const; }
    });
    Promise.all(jobs).then((entries) => {
      if (!active) return;
      setComparisonDetails(Object.fromEntries(entries));
      setComparisonLoading(false);
    });
    return () => { active = false; };
  }, [selectedRace]);

  if (!meeting || !selectedRace) return null;
  const resolvedRunner = detail.runner ?? selectedRunner;
  const runs = recentRuns(resolvedRunner);
  const summary = sectionalSummary(resolvedRunner);
  const intel = performanceIntel(resolvedRunner, selectedRace, display(meeting.date, ""));
  const allComparisonRows: ComparisonRunner[] = selectedRace.runners.map((runner, index) => {
    const resolved = comparisonDetails[index] ?? runner;
    return { index, runner: resolved, intel: performanceIntel(resolved, selectedRace, display(meeting.date, "")) };
  });
  const comparisonRows = allComparisonRows.filter((row) => filterComparison(row, comparisonFilter)).sort((a, b) => compareRows(a, b, comparisonSort, sortDirection));

  const ratedByLatest = [...allComparisonRows].filter((row) => row.intel.latestRatingValue !== null).sort((a, b) => (b.intel.latestRatingValue ?? -Infinity) - (a.intel.latestRatingValue ?? -Infinity));
  const latestLeader = ratedByLatest[0] ?? null;
  const peakLeader = [...allComparisonRows].filter((row) => row.intel.peakRatingValue !== null).sort((a, b) => (b.intel.peakRatingValue ?? -Infinity) - (a.intel.peakRatingValue ?? -Infinity))[0] ?? null;
  const biggestImprover = [...allComparisonRows].filter((row) => row.intel.ratingTrendDeltaValue !== null && row.intel.ratingTrendDeltaValue > 0).sort((a, b) => (b.intel.ratingTrendDeltaValue ?? -Infinity) - (a.intel.ratingTrendDeltaValue ?? -Infinity))[0] ?? null;
  const distanceLeader = [...allComparisonRows].filter((row) => row.intel.distanceRunCount > 0).sort((a, b) => {
    if (a.intel.distanceRunCount !== b.intel.distanceRunCount) return b.intel.distanceRunCount - a.intel.distanceRunCount;
    const aBest = a.intel.distanceBestFinish ?? Infinity;
    const bBest = b.intel.distanceBestFinish ?? Infinity;
    if (aBest !== bBest) return aBest - bBest;
    return (b.intel.latestRatingValue ?? -Infinity) - (a.intel.latestRatingValue ?? -Infinity);
  })[0] ?? null;
  const weakEvidenceCount = allComparisonRows.filter(isLimited).length;

  function chooseSort(next: ComparisonSort) {
    if (comparisonSort === next) setSortDirection((current) => current === "desc" ? "asc" : "desc");
    else {
      setComparisonSort(next);
      setSortDirection(next === "runner" || next === "recency" ? "asc" : "desc");
    }
  }
  function sortMark(key: ComparisonSort): string { return comparisonSort === key ? (sortDirection === "desc" ? " ↓" : " ↑") : ""; }

  return (
    <section className="eiq-performance-v1" aria-label="Performance workspace" data-edgeiq-workspace-key="PERFORMANCE">
      <header className="eiq-performance-v1__header">
        <div><p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p><h1>Performance</h1></div>
        <strong>{selectedRace.runners.length} runners</strong>
      </header>

      <nav className="eiq-performance-v1__race-tabs" aria-label="Meeting races">
        {meeting.races.map((race) => <button key={race.raceKey} type="button" className={race.raceKey === selectedRace.raceKey ? "is-active" : ""} onClick={() => onRaceChange(race.raceKey)}><strong>R{race.raceNumber}</strong><span>{display(race.raceTime)}</span></button>)}
      </nav>

      <section className="eiq-performance-v1__card">
        <header><div><h2>{raceTitle(selectedRace)}</h2><p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p></div></header>
        <section className="eiq-performance-v1__relative" aria-label="Race relative performance intelligence">
          <header><div><span>RACE-RELATIVE INTELLIGENCE</span><strong>TRACEABLE EVIDENCE</strong></div><p>No composite score · no pricing impact</p></header>
          <div>
            <article><span>TOP CURRENT RATING</span><strong>{comparisonName(latestLeader)}</strong><small>{latestLeader ? latestLeader.intel.latestRating : "NO RATED EVIDENCE"}</small></article>
            <article><span>STRONGEST PEAK</span><strong>{comparisonName(peakLeader)}</strong><small>{peakLeader ? peakLeader.intel.peakRating : "NO RATED EVIDENCE"}</small></article>
            <article><span>BIGGEST IMPROVER</span><strong>{comparisonName(biggestImprover)}</strong><small>{biggestImprover ? biggestImprover.intel.ratingTrend : "NO POSITIVE TREND"}</small></article>
            <article><span>DISTANCE SIGNAL</span><strong>{comparisonName(distanceLeader)}</strong><small>{distanceLeader ? distanceLeader.intel.distanceEvidence : "NO EXACT-DISTANCE RUNS"}</small></article>
            <article><span>WEAK EVIDENCE</span><strong>{weakEvidenceCount} RUNNER{weakEvidenceCount === 1 ? "" : "S"}</strong><small>&lt;2 prior runs or no rated run</small></article>
          </div>
        </section>

        <section className="eiq-performance-v1__comparison" aria-label="Field performance comparison">
          <header><div><span>FIELD COMPARISON</span><strong>STRICT-PRIOR</strong></div><p>{comparisonLoading ? "Loading runner evidence…" : `${comparisonRows.length}/${allComparisonRows.length} runners shown`}</p></header>
          <div className="eiq-performance-v1__comparison-controls" aria-label="Performance comparison filters">
            <div>{FILTERS.map((filter) => <button key={filter.key} type="button" className={comparisonFilter === filter.key ? "is-active" : ""} onClick={() => setComparisonFilter(filter.key)}>{filter.label}</button>)}</div>
            <span>Click a column heading to sort</span>
          </div>
          <div className="eiq-performance-v1__comparison-table">
            <div className="eiq-performance-v1__comparison-head">
              <span>#</span>
              <button type="button" onClick={() => chooseSort("runner")}>Runner{sortMark("runner")}</button>
              <button type="button" onClick={() => chooseSort("latest")}>Latest{sortMark("latest")}</button>
              <button type="button" onClick={() => chooseSort("peak")}>Peak{sortMark("peak")}</button>
              <button type="button" onClick={() => chooseSort("trajectory")}>Trajectory{sortMark("trajectory")}</button>
              <span>Recent form</span>
              <button type="button" onClick={() => chooseSort("recency")}>Recency{sortMark("recency")}</button>
              <button type="button" onClick={() => chooseSort("distance")}>Distance{sortMark("distance")}</button>
              <button type="button" onClick={() => chooseSort("evidence")}>Evidence{sortMark("evidence")}</button>
            </div>
            {comparisonRows.map(({ index, runner, intel }) => <button key={`${officialNumber(runner)}-${runnerName(runner)}-${index}`} type="button" className={`eiq-performance-v1__comparison-row${index === selectedRunnerIndex ? " is-active" : ""}`} onClick={() => setSelectedRunnerIndex(index)}><span>{officialNumber(runner)}</span><strong>{runnerName(runner)}</strong><span>{intel.latestRating}</span><span>{intel.peakRating}</span><span className={`is-${intel.ratingTrendTone}`}>{intel.ratingTrend}</span><span>{intel.recentForm}</span><span>{intel.recency}</span><span>{intel.distanceEvidence}</span><span>{intel.ratingCoverage}</span></button>)}
            {!comparisonRows.length && !comparisonLoading ? <p className="eiq-performance-v1__comparison-empty">No runners match this evidence filter.</p> : null}
          </div>
        </section>

        <div className="eiq-performance-v1__layout">
          <aside className="eiq-performance-v1__runners">
            {selectedRace.runners.map((runner, index) => <button key={`${officialNumber(runner)}-${runnerName(runner)}-${index}`} type="button" className={index === selectedRunnerIndex ? "is-active" : ""} onClick={() => setSelectedRunnerIndex(index)}><span>{officialNumber(runner)}</span><strong>{runnerName(runner)}</strong></button>)}
          </aside>
          <div className="eiq-performance-v1__detail">
            {selectedRunner ? <>
              <div className="eiq-performance-v1__runner-head"><div><span>#{officialNumber(selectedRunner)}</span><h3>{runnerName(selectedRunner)}</h3></div><dl><div><dt>Jockey</dt><dd>{display(selectedRunner.official.jockey)}</dd></div><div><dt>Trainer</dt><dd>{display(selectedRunner.official.trainer)}</dd></div><div><dt>Weight</dt><dd>{display(selectedRunner.official.weight)}</dd></div></dl></div>
              <section className="eiq-performance-v1__intelligence" aria-label="Governed performance intelligence">
                <header><div><span>PERFORMANCE INTELLIGENCE</span><strong>{intel.historyCount} PRIOR RUN{intel.historyCount === 1 ? "" : "S"}</strong></div><p>Strict-prior evidence only</p></header>
                <div>
                  <article><span>LATEST RATING</span><strong>{intel.latestRating}</strong><small>{intel.ratingCoverage}</small></article>
                  <article><span>PEAK RATING</span><strong>{intel.peakRating}</strong><small>Last {intel.historyCount || 0} supplied runs</small></article>
                  <article><span>RATING TRAJECTORY</span><strong>{intel.ratingTrend}</strong><small>Latest vs prior rated runs</small></article>
                  <article><span>RECENT FORM</span><strong>{intel.recentForm}</strong><small>Most recent first</small></article>
                  <article><span>RECENCY</span><strong>{intel.recency}</strong><small>Days since latest supplied run</small></article>
                  <article><span>DISTANCE EVIDENCE</span><strong>{intel.distanceEvidence}</strong><small>Exact current-distance matches</small></article>
                </div>
              </section>
              <section className="eiq-performance-v1__sectionals" aria-label="Governed sectional evidence"><header><span>{summaryValue(summary, "label", "NO SECTIONAL HISTORY")}</span><strong>{summaryValue(summary, "support")}</strong></header><div><article><span>SECTIONAL WEAPON</span><strong>{summaryValue(summary, "sectionalWeapon")}</strong></article><article><span>LATE POWER</span><strong>{summaryValue(summary, "latePower")}</strong></article><article><span>EARLY SPEED</span><strong>{summaryValue(summary, "earlySpeed")}</strong></article><article><span>CONSISTENCY</span><strong>{summaryValue(summary, "consistency")}</strong></article><article><span>TRAJECTORY</span><strong>{summaryValue(summary, "trajectory")}</strong></article></div></section>
            </> : null}
            {detail.loading ? <p className="eiq-performance-v1__message">Loading…</p> : null}
            {!detail.loading && detail.error ? <p className="eiq-performance-v1__message">{detail.error}</p> : null}
            {!detail.loading && !detail.error && runs.length ? <div className="eiq-performance-v1__runs"><div className="eiq-performance-v1__runs-head"><span>Date</span><span>Track</span><span>Dist.</span><span>Class</span><span>Going</span><span>Finish</span><span>Margin</span><span>Rating</span><span>Early</span><span>Late</span></div>{runs.map((run, index) => { const record = asRecord(run); return <div className="eiq-performance-v1__run" key={index}><span>{first(record,["date","race_date","meeting_date","raceDate"])}</span><span>{first(record,["track","meeting","venue","track_name","meetingName"])}</span><span>{first(record,["distance","dist","race_distance"])}</span><span>{first(record,["class","race_class","raceClass"])}</span><span>{first(record,["going","track_condition","trackCondition","condition"])}</span><span>{first(record,["finish","position","placing","place"])}</span><span>{first(record,["margin","margin_beaten","beaten_margin","beatenMargin"])}</span><span>{first(record,["rating","wfa","form_rating","performance_rating","figure"])}</span><span>{first(record,["early_speed","earlySpeed","early","early_sectional","earlySectional"])}</span><span>{first(record,["late_speed","lateSpeed","late","late_sectional","lateSectional"])}</span></div>; })}</div> : null}
            {!detail.loading && !detail.error && !runs.length ? <p className="eiq-performance-v1__message">No performance history supplied.</p> : null}
          </div>
        </div>
      </section>
    </section>
  );
}
