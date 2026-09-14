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
  peakRating: string;
  ratingTrend: string;
  recentForm: string;
  recency: string;
  distanceEvidence: string;
  ratingCoverage: string;
};

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
  if (ratings.length >= 2) {
    const prior = ratings.slice(1);
    const priorAverage = prior.reduce((sum, value) => sum + value, 0) / prior.length;
    const delta = latestRatingValue! - priorAverage;
    if (delta >= 2) ratingTrend = `UP +${delta.toFixed(1)}`;
    else if (delta <= -2) ratingTrend = `DOWN ${delta.toFixed(1)}`;
    else ratingTrend = `STABLE ${delta >= 0 ? "+" : ""}${delta.toFixed(1)}`;
  }

  const form = rows
    .map((record) => first(record, ["finish", "position", "placing", "place"], ""))
    .filter(Boolean)
    .join("-");

  let recency = "LIMITED DATA";
  const latestDateRaw = rows.length ? first(rows[0], ["date", "race_date", "meeting_date", "raceDate"], "") : "";
  const currentDate = Date.parse(meetingDate);
  const latestDate = Date.parse(latestDateRaw);
  if (Number.isFinite(currentDate) && Number.isFinite(latestDate) && currentDate > latestDate) {
    const days = Math.round((currentDate - latestDate) / 86400000);
    recency = `${days}D`;
  }

  const targetDistance = distanceMetres(race.distance);
  const distanceRows = targetDistance === null ? [] : rows.filter((record) => distanceMetres(first(record, ["distance", "dist", "race_distance"], "")) === targetDistance);
  const distanceFinishes = distanceRows.map(finishPosition).filter((value): value is number => value !== null);
  let distanceEvidence = "NO MATCHING RUNS";
  if (distanceRows.length) {
    const best = distanceFinishes.length ? Math.min(...distanceFinishes) : null;
    distanceEvidence = best === null ? `${distanceRows.length} RUN${distanceRows.length === 1 ? "" : "S"}` : `${distanceRows.length} RUN${distanceRows.length === 1 ? "" : "S"} · BEST ${best}`;
  }

  return {
    historyCount: rows.length,
    ratedCount: ratings.length,
    latestRating: latestRatingValue === null ? "LIMITED DATA" : latestRatingValue.toFixed(1),
    peakRating: peakRatingValue === null ? "LIMITED DATA" : peakRatingValue.toFixed(1),
    ratingTrend,
    recentForm: form || "LIMITED DATA",
    recency,
    distanceEvidence,
    ratingCoverage: rows.length ? `${ratings.length}/${rows.length} RATED` : "NO HISTORY",
  };
}

export function PerformanceWorkspace({ meeting, selectedRaceKey, onRaceChange }: PerformanceWorkspaceProps) {
  const selectedRace = useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);

  const [selectedRunnerIndex, setSelectedRunnerIndex] = useState(0);
  const [detail, setDetail] = useState<RunnerLoad>({ runner: null, loading: false, error: "" });

  useEffect(() => { setSelectedRunnerIndex(0); }, [selectedRace?.raceKey]);

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

  if (!meeting || !selectedRace) return null;
  const resolvedRunner = detail.runner ?? selectedRunner;
  const runs = recentRuns(resolvedRunner);
  const summary = sectionalSummary(resolvedRunner);
  const intel = performanceIntel(resolvedRunner, selectedRace, display(meeting.date, ""));

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
