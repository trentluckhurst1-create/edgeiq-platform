import { useMemo, useState } from "react";
import type { CareerStats, FormHistoryRow, RatingDisplayRow } from "../App";
import { getSilksUrl, silkFallback } from "../utils/silks";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  historyByHorse: Map<string, FormHistoryRow[]>;
  careerStats?: CareerStats | null;
  raceStandard?: Record<string, string> | null;
};

type SortKey =
  | "horseNo"
  | "today"
  | "ls1"
  | "ls2"
  | "ls3"
  | "ls4"
  | "ls5"
  | "avg3"
  | "avg5"
  | "form"
  | "peak"
  | "gap"
  | "standard"
  | "class"
  | "distance"
  | "speed"
  | "recency"
  | "momentum"
  | "runs"
  | "consistency"
  | "upside"
  | "regression"
  | "suitability"
  | "tripAdj"
  | "weightAdj"
  | "jockeyAdj"
  | "jockeyStat"
  | "handicapperTotal"
  | "beforeHandicapper"
  | "finalRating";

type SortState = { key: SortKey | null; direction: "desc" | "asc" };
type ProfileLabel = "PEAKING" | "CONSISTENT" | "REGRESSING" | "EXPOSED" | "UNKNOWN";

function safe(v: unknown): string {
  const s = String(v ?? "").trim();
  if (!s || s.toLowerCase() === "nan" || s.toLowerCase() === "null") return "-";
  return s;
}

function num(v: unknown): number | null {
  const n = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function fmt(v: unknown, digits = 1): string {
  const n = num(v);
  return n === null ? "-" : n.toFixed(digits);
}


function pct(v: unknown, digits = 1): string {
  const n = num(v);
  if (n === null) return "-";
  return `${(n * 100).toFixed(digits)}%`;
}

function roi(v: unknown): string {
  const n = num(v);
  if (n === null) return "-";
  return `${(n * 100).toFixed(1)}%`;
}

function tierClass(value: unknown): string {
  return `tier-${safe(value).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}
function signed(v: unknown, digits = 1): string {
  const n = num(v);
  if (n === null) return "-";
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}`;
}

function adj(v: unknown): string {
  const n = num(v);
  if (n === null) return "-";
  return n.toFixed(3);
}

function historyFor(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): FormHistoryRow[] {
  return historyByHorse.get(row.horseKey) ?? historyByHorse.get(row.matchKey) ?? [];
}

function officialRuns(rows: FormHistoryRow[]): FormHistoryRow[] {
  return rows.filter((r) => r.isOfficialRace).sort((a, b) => new Date(b.runDate || 0).getTime() - new Date(a.runDate || 0).getTime());
}

function lastFiveRatings(row: RatingDisplayRow, historyByHorse?: Map<string, FormHistoryRow[]>): Array<number | null> {
  const fromSummary = [row.ls1, row.ls2, row.ls3, row.ls4, row.ls5].map((x) => num(x));
  if (fromSummary.some((x) => x !== null)) return fromSummary;
  if (!historyByHorse) return fromSummary;
  const fromHistory = officialRuns(historyFor(row, historyByHorse)).slice(0, 5).map((r) => num(r.runRating));
  while (fromHistory.length < 5) fromHistory.push(null);
  return fromHistory.slice(0, 5);
}

function cleanRatings(vals: Array<number | null>): number[] {
  return vals.filter((x): x is number => x !== null && Number.isFinite(x));
}

function avg(vals: number[]): number | null {
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
}

function avgLast(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>, take: number): number | null {
  const vals = cleanRatings(lastFiveRatings(row, historyByHorse)).slice(0, take);
  return avg(vals);
}

function peakRating(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): number | null {
  return num(row.peak) ?? (cleanRatings(lastFiveRatings(row, historyByHorse)).length ? Math.max(...cleanRatings(lastFiveRatings(row, historyByHorse))) : null);
}

function gapToPeak(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): number | null {
  const peak = peakRating(row, historyByHorse);
  const today = num(row.todayRating);
  if (peak === null || today === null) return null;
  return peak - today;
}

function ratingVsStandard(row: RatingDisplayRow, standard: number): number | null {
  const today = num(row.todayRating);
  return today === null ? null : today - standard;
}

function standardTone(v: number | null): string {
  if (v === null) return "standard-none";
  if (v >= 0) return "standard-above";
  if (v >= -3) return "standard-near";
  return "standard-below";
}

function scoreTone(v: number | null): string {
  if (v === null) return "standard-none";
  if (v >= 72) return "standard-above";
  if (v >= 52) return "standard-near";
  return "standard-below";
}
function pointTone(v: number | null): string {
  if (v === null || Math.abs(v) < 0.05) return "standard-none";
  return v > 0 ? "standard-above" : "standard-below";
}

function consistencyScore(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): number | null {
  const vals = cleanRatings(lastFiveRatings(row, historyByHorse));
  if (vals.length < 2) return null;
  const mean = avg(vals) ?? 0;
  const variance = vals.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / vals.length;
  return Math.max(0, Math.min(100, 100 - Math.sqrt(variance) * 7.5));
}

function upsideScore(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): number | null {
  const gap = gapToPeak(row, historyByHorse);
  const today = num(row.todayRating);
  if (gap === null || today === null) return null;
  const recentMomentum = num(row.momentumAdj) ?? 0;
  return Math.max(0, Math.min(100, 48 + gap * 5 + recentMomentum * 14));
}

function regressionRisk(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): number | null {
  const vals = cleanRatings(lastFiveRatings(row, historyByHorse));
  if (vals.length < 3) return null;
  const latest = vals[0];
  const a3 = avg(vals.slice(0, 3)) ?? latest;
  const a5 = avg(vals.slice(0, 5)) ?? a3;
  const drop = Math.max(0, a5 - latest) + Math.max(0, a3 - latest) * 0.6;
  const momentumDrag = Math.max(0, -(num(row.momentumAdj) ?? 0)) * 8;
  return Math.max(0, Math.min(100, 22 + drop * 7 + momentumDrag));
}

function suitabilityScore(row: RatingDisplayRow): number | null {
  const adjustments = [row.classAdj, row.distanceAdj, row.speedAdj, row.recencyAdj, row.momentumAdj].map(num).filter((x): x is number => x !== null);
  if (!adjustments.length) return null;
  const raw = adjustments.reduce((sum, x) => sum + x, 0);
  return Math.max(0, Math.min(100, 55 + raw * 16));
}

function profileLabel(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): ProfileLabel {
  const vals = cleanRatings(lastFiveRatings(row, historyByHorse));
  if (vals.length < 2 || (row.runsUsed ?? vals.length) === 0) return "UNKNOWN";
  const latest = vals[0];
  const a3 = avg(vals.slice(0, 3));
  const a5 = avg(vals.slice(0, 5));
  const consistency = consistencyScore(row, historyByHorse);
  const risk = regressionRisk(row, historyByHorse);
  const gap = gapToPeak(row, historyByHorse);
  if (a3 !== null && latest >= a3 + 1.5 && (gap === null || gap <= 2.5)) return "PEAKING";
  if (risk !== null && risk >= 66) return "REGRESSING";
  if (consistency !== null && consistency >= 78) return "CONSISTENT";
  if ((row.runsUsed ?? vals.length) >= 8 && gap !== null && gap >= 6) return "EXPOSED";
  if (a5 !== null && latest < a5 - 3) return "REGRESSING";
  return "CONSISTENT";
}

function defaultSort(a: RatingDisplayRow, b: RatingDisplayRow): number {
  if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
  const ah = a.horseNo ?? 9999;
  const bh = b.horseNo ?? 9999;
  if (ah !== bh) return ah - bh;
  return a.horse.localeCompare(b.horse);
}

function sortValue(row: RatingDisplayRow, key: SortKey, historyByHorse: Map<string, FormHistoryRow[]>, standard: number): number | null {
  const l5 = lastFiveRatings(row, historyByHorse);
  if (key === "horseNo") return row.horseNo;
  if (key === "today") return row.todayRating;
  if (key === "ls1") return l5[0];
  if (key === "ls2") return l5[1];
  if (key === "ls3") return l5[2];
  if (key === "ls4") return l5[3];
  if (key === "ls5") return l5[4];
  if (key === "avg3") return avgLast(row, historyByHorse, 3) ?? row.recentSimpleAvg ?? null;
  if (key === "avg5") return avgLast(row, historyByHorse, 5) ?? row.baseLast5 ?? null;
  if (key === "form") return row.formRating ?? null;
  if (key === "peak") return peakRating(row, historyByHorse);
  if (key === "gap") return gapToPeak(row, historyByHorse);
  if (key === "standard") return ratingVsStandard(row, standard);
  if (key === "class") return row.classAdj ?? null;
  if (key === "distance") return row.distanceAdj ?? null;
  if (key === "speed") return row.speedAdj ?? null;
  if (key === "recency") return row.recencyAdj ?? null;
  if (key === "momentum") return row.momentumAdj ?? null;
  if (key === "runs") return row.runsUsed ?? null;
  if (key === "consistency") return consistencyScore(row, historyByHorse);
  if (key === "upside") return upsideScore(row, historyByHorse);
  if (key === "regression") return regressionRisk(row, historyByHorse);
  if (key === "suitability") return suitabilityScore(row);
  if (key === "tripAdj") return row.tripAdjPoints ?? null;
  if (key === "weightAdj") return row.weightAdjPoints ?? null;
  if (key === "jockeyAdj") return row.jockeyAdjPoints ?? null;
  if (key === "jockeyStat") return row.jockeyStatRatingPoints ?? null;
  if (key === "handicapperTotal") return row.handicapperAdjTotal ?? null;
  if (key === "beforeHandicapper") return row.eliteTodayRatingBeforeHandicapper ?? null;
  if (key === "finalRating") return row.handicapperRating ?? row.todayRating ?? null;
  return null;
}

function dateShort(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return safe(value);
  return d.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "2-digit" });
}


function ordinal(value: string): string {
  const n = num(value);
  if (n === null) return safe(value);
  const whole = Math.trunc(n);
  const suffix = whole % 100 >= 11 && whole % 100 <= 13 ? "th" : whole % 10 === 1 ? "st" : whole % 10 === 2 ? "nd" : whole % 10 === 3 ? "rd" : "th";
  return `${whole}${suffix}`;
}

function resultLine(run: FormHistoryRow): string {
  const finish = safe(run.finishPos);
  const margin = safe(run.margin);
  const parts = [];
  if (finish !== "-") parts.push(`Finished ${ordinal(finish)}`);
  if (margin !== "-") parts.push(`beaten ${margin}${/l$/i.test(margin) ? "" : "L"}`);
  return parts.length ? parts.join(", ") : "Result detail unavailable";
}

function flagLine(run: FormHistoryRow): string {
  const text = `${safe(run.raceClass)} ${safe(run.trackCondition)} ${safe(run.margin)} ${safe(run.jockey)}`.toLowerCase();
  const flags = ["held up", "checked", "wide", "slow", "vet", "gear"].filter((flag) => text.includes(flag));
  return flags.length ? flags.join(" | ").toUpperCase() : "Insufficient run context";
}

function RunRatingCell({ value, run }: { value: number | null; run?: FormHistoryRow | null }) {
  return (
    <span className="edgeiq-run-rating-hover">
      <strong>{fmt(value)}</strong>
      <span className="edgeiq-run-tooltip" role="tooltip">
        {run ? (
          <>
            <span className="tooltip-kicker">{safe(run.runType) || "RACE"}</span>
            <strong>{safe(run.track)} {run.distance ? `${run.distance}m` : ""}</strong>
            <em>{dateShort(run.runDate)} | {safe(run.raceClass)} | {safe(run.trackCondition)}</em>
            <span>{resultLine(run)}</span>
            <span>Jockey: {safe(run.jockey)} | SP: {safe(run.sp)}</span>
            <span>Context: {flagLine(run)}</span>
            <span>Run rating: {fmt(run.runRating)}</span>
            <span className="tooltip-flags">{flagLine(run)}</span>
          </>
        ) : (
          <span>Insufficient run context</span>
        )}
      </span>
    </span>
  );
}
function SortButton({ label, sortKey, sort, onSort }: { label: string; sortKey: SortKey; sort: SortState; onSort: (key: SortKey) => void }) {
  const suffix = sort.key === sortKey ? (sort.direction === "desc" ? " D" : " A") : "";
  return <button onClick={() => onSort(sortKey)}>{label}{suffix}</button>;
}

export default function RatingsTab({ runners, selectedHorseKey, onSelectHorse, historyByHorse, careerStats, raceStandard }: Props) {
  const [sort, setSort] = useState<SortState>({ key: null, direction: "desc" });
  const [hideScratched, setHideScratched] = useState(true);
  const live = runners.filter((r) => !r.isScratched);
  const topRated = [...live].sort((a, b) => (b.todayRating ?? -999) - (a.todayRating ?? -999))[0] ?? null;
  const fieldAvg = live.length ? live.reduce((sum, r) => sum + (r.todayRating ?? 0), 0) / live.length : null;
  const standard = num(raceStandard?.winning_standard) ?? topRated?.todayRating ?? (fieldAvg !== null ? fieldAvg + 5 : 91);
  const floor = num(raceStandard?.competitive_floor) ?? standard - 3;
  const ceiling = num(raceStandard?.competitive_ceiling) ?? standard + 2;
  const standardLabel = raceStandard?.standard_label || "LIVE FIELD STANDARD";

  function cycleSort(key: SortKey): void {
    setSort((current) => {
      if (current.key !== key) return { key, direction: "desc" };
      if (current.direction === "desc") return { key, direction: "asc" };
      return { key: null, direction: "desc" };
    });
  }

  const ranked = useMemo(() => {
    const rows = hideScratched ? [...live] : [...runners];
    if (!sort.key) return rows.sort(defaultSort);
    return rows.sort((a, b) => {
      if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
      const av = sortValue(a, sort.key!, historyByHorse, standard);
      const bv = sortValue(b, sort.key!, historyByHorse, standard);
      if (av === null && bv === null) return defaultSort(a, b);
      if (av === null) return 1;
      if (bv === null) return -1;
      const diff = sort.direction === "desc" ? bv - av : av - bv;
      return diff || defaultSort(a, b);
    });
  }, [hideScratched, live, runners, sort, historyByHorse, standard]);

  const selected = runners.find((r) => r.horseKey === selectedHorseKey) ?? ranked[0] ?? runners[0] ?? null;
  const selectedHistory = selected ? historyFor(selected, historyByHorse) : [];
  const selectedRuns = officialRuns(selectedHistory).slice(0, 5);
  const selectedL5 = selected ? lastFiveRatings(selected, historyByHorse) : [null, null, null, null, null];
  const selectedAvg3 = selected ? avgLast(selected, historyByHorse, 3) ?? selected.recentSimpleAvg ?? null : null;
  const selectedAvg5 = selected ? avgLast(selected, historyByHorse, 5) ?? selected.baseLast5 ?? null : null;
  const selectedVsStandard = selected ? ratingVsStandard(selected, standard) : null;
  const selectedGap = selected ? gapToPeak(selected, historyByHorse) : null;
  const selectedConsistency = selected ? consistencyScore(selected, historyByHorse) : null;
  const selectedUpside = selected ? upsideScore(selected, historyByHorse) : null;
  const selectedRisk = selected ? regressionRisk(selected, historyByHorse) : null;
  const selectedSuitability = selected ? suitabilityScore(selected) : null;
  const selectedProfile = selected ? profileLabel(selected, historyByHorse) : "UNKNOWN";

  return (
    <div className="edgeiq-ratings terminal-panel-stack ratings-deep-dive">
      <section className="edgeiq-winning-standard terminal-card">
        <div><div className="edgeiq-ws-kicker">TODAY'S WINNING STANDARD</div><h3>Expected Winning Rating: {fmt(standard)}</h3><p>{standardLabel}</p></div>
        <div className="winning-standard-grid">
          <div><span>Competitive Range</span><strong>{fmt(floor)}-{fmt(ceiling)}</strong></div>
          <div><span>Race Depth</span><strong>{fmt(raceStandard?.race_depth_score)}</strong></div>
          <div><span>Field Avg</span><strong>{fmt(fieldAvg)}</strong></div>
          <div><span>Top Rating</span><strong>{fmt(topRated?.todayRating)}</strong></div>
        </div>
      </section>

      <div className="edgeiq-ratings-toolbar terminal-card compact-toolbar">
        <div className="edgeiq-ws-kicker">RATING ANALYSIS</div>
        <button className={hideScratched ? "is-active" : ""} onClick={() => setHideScratched((v) => !v)}>{hideScratched ? `Show SCR (${runners.filter((r) => r.isScratched).length})` : "Hide SCR"}</button>
      </div>

      <div className="edgeiq-ratings-grid ratings-analysis-grid">
        <section className="edgeiq-ws-card terminal-card ratings-table-card">
          <div className="edgeiq-ws-head"><div className="edgeiq-ws-kicker">FIELD RATINGS</div></div>
          <div className="edgeiq-ws-table-wrap aligned-table-wrap ratings-table-scroll">
            <table className="edgeiq-ws-table edgeiq-ratings-table aligned-runner-table ratings-analysis-table ratings-paid-table">
              <colgroup><col className="rate-no" /><col className="rate-runner" /><col span={29} /></colgroup>
              <thead><tr>
                <th><SortButton label="No" sortKey="horseNo" sort={sort} onSort={cycleSort} /></th>
                <th>Runner</th>
                <th className="num"><SortButton label="Today" sortKey="today" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="1LS" sortKey="ls1" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="2LS" sortKey="ls2" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="3LS" sortKey="ls3" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="4LS" sortKey="ls4" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="5LS" sortKey="ls5" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Avg3" sortKey="avg3" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Avg5" sortKey="avg5" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Form" sortKey="form" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Peak" sortKey="peak" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Gap" sortKey="gap" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Vs Std" sortKey="standard" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Class" sortKey="class" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Dist" sortKey="distance" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Speed" sortKey="speed" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Rec" sortKey="recency" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Mom" sortKey="momentum" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Cons" sortKey="consistency" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Upside" sortKey="upside" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Risk" sortKey="regression" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Suit" sortKey="suitability" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Trip" sortKey="tripAdj" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Wgt" sortKey="weightAdj" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Jock" sortKey="jockeyAdj" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="J Stat" sortKey="jockeyStat" sort={sort} onSort={cycleSort} /></th>
                <th>J Tier</th>
                <th className="num"><SortButton label="Hcp" sortKey="handicapperTotal" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Before" sortKey="beforeHandicapper" sort={sort} onSort={cycleSort} /></th>
                <th className="num"><SortButton label="Final" sortKey="finalRating" sort={sort} onSort={cycleSort} /></th>
                <th>Profile</th>
                <th className="num"><SortButton label="Runs" sortKey="runs" sort={sort} onSort={cycleSort} /></th>
              </tr></thead>
              <tbody>{ranked.map((row, idx) => {
                const l5 = lastFiveRatings(row, historyByHorse);
                const detailRuns = officialRuns(historyFor(row, historyByHorse)).slice(0, 5);
                const vs = ratingVsStandard(row, standard);
                const consistency = consistencyScore(row, historyByHorse);
                const upside = upsideScore(row, historyByHorse);
                const risk = regressionRisk(row, historyByHorse);
                const suitability = suitabilityScore(row);
                const profile = profileLabel(row, historyByHorse);
                return <tr key={row.id || `${row.horseKey}-${idx}`} className={`${selected?.horseKey === row.horseKey ? "is-selected" : ""} ${row.isScratched ? "is-scratched" : ""}`} onClick={() => onSelectHorse(row.horseKey)}>
                  <td className="num strong">{row.isScratched ? "SCR" : safe(row.horseNo)}</td>
                  <td><div className="edgeiq-runner aligned-runner"><img src={getSilksUrl(row.horse, row.silkUrl)} alt="" onError={silkFallback} /><div className="edgeiq-runner-meta"><strong>{safe(row.horse)}</strong><span>Bar {safe(row.barrier)} | {safe(row.jockey)}</span></div></div></td>
                  <td className="num strong">{fmt(row.todayRating)}</td>
                  <td className="num"><RunRatingCell value={l5[0]} run={detailRuns[0]} /></td><td className="num"><RunRatingCell value={l5[1]} run={detailRuns[1]} /></td><td className="num"><RunRatingCell value={l5[2]} run={detailRuns[2]} /></td><td className="num"><RunRatingCell value={l5[3]} run={detailRuns[3]} /></td><td className="num"><RunRatingCell value={l5[4]} run={detailRuns[4]} /></td>
                  <td className="num">{fmt(avgLast(row, historyByHorse, 3) ?? row.recentSimpleAvg)}</td><td className="num">{fmt(avgLast(row, historyByHorse, 5) ?? row.baseLast5)}</td><td className="num">{fmt(row.formRating)}</td><td className="num">{fmt(peakRating(row, historyByHorse))}</td><td className="num">{fmt(gapToPeak(row, historyByHorse))}</td><td className={`num strong ${standardTone(vs)}`}>{vs === null ? "-" : signed(vs)}</td>
                  <td className="num">{adj(row.classAdj)}</td><td className="num">{adj(row.distanceAdj)}</td><td className="num">{adj(row.speedAdj)}</td><td className="num">{adj(row.recencyAdj)}</td><td className="num">{adj(row.momentumAdj)}</td><td className={`num ${scoreTone(consistency)}`}>{fmt(consistency, 0)}</td><td className={`num ${scoreTone(upside)}`}>{fmt(upside, 0)}</td><td className={`num ${risk !== null && risk >= 66 ? "standard-below" : risk !== null && risk >= 45 ? "standard-near" : "standard-above"}`}>{fmt(risk, 0)}</td><td className={`num ${scoreTone(suitability)}`}>{fmt(suitability, 0)}</td><td className={`num ${pointTone(row.tripAdjPoints ?? null)}`}>{signed(row.tripAdjPoints)}</td><td className={`num ${pointTone(row.weightAdjPoints ?? null)}`}>{signed(row.weightAdjPoints)}</td><td className={`num ${pointTone(row.jockeyAdjPoints ?? null)}`}>{signed(row.jockeyAdjPoints)}</td><td className={`num ${pointTone(row.jockeyStatRatingPoints ?? null)}`}>{signed(row.jockeyStatRatingPoints)}</td><td><span className={`jockey-tier-pill ${tierClass(row.jockeyTier)}`}>{safe(row.jockeyTier || "UNKNOWN")}</span></td><td className={`num strong ${pointTone(row.handicapperAdjTotal ?? null)}`}>{signed(row.handicapperAdjTotal)}</td><td className="num">{fmt(row.eliteTodayRatingBeforeHandicapper)}</td><td className="num strong">{fmt(row.handicapperRating ?? row.todayRating)}</td><td><span className={`rating-profile-pill profile-${profile.toLowerCase()}`}>{profile}</span>{(row.jockeyAdjPoints ?? 0) < 0 ? <span className="jockey-penalty-chip">Jockey penalty applied</span> : null}</td><td className="num">{fmt(row.runsUsed, 0)}</td>
                </tr>;
              })}</tbody>
            </table>
          </div>
        </section>

        <aside className="edgeiq-rating-panel terminal-card ratings-detail-panel">
          {selected ? <>
            <div className="edgeiq-rating-profile"><img src={getSilksUrl(selected.horse, selected.silkUrl)} alt="" onError={silkFallback} /><div><div className="edgeiq-ws-kicker">SELECTED RATING PROFILE</div><h3>{safe(selected.horse)}</h3><p>No {safe(selected.horseNo)} | Bar {safe(selected.barrier)} | Runs {fmt(selected.runsUsed, 0)}</p></div></div>
            <div className="edgeiq-rating-price-grid rating-factor-grid rating-intel-grid">
              <div><span>Today</span><strong>{fmt(selected.todayRating)}</strong></div><div><span>Vs Standard</span><strong className={standardTone(selectedVsStandard)}>{selectedVsStandard === null ? "-" : signed(selectedVsStandard)}</strong></div><div><span>Profile</span><strong>{selectedProfile}</strong></div><div><span>Suitability</span><strong className={scoreTone(selectedSuitability)}>{fmt(selectedSuitability, 0)}</strong></div><div><span>Consistency</span><strong className={scoreTone(selectedConsistency)}>{fmt(selectedConsistency, 0)}</strong></div><div><span>Upside</span><strong className={scoreTone(selectedUpside)}>{fmt(selectedUpside, 0)}</strong></div><div><span>Regression Risk</span><strong className={selectedRisk !== null && selectedRisk >= 66 ? "standard-below" : selectedRisk !== null && selectedRisk >= 45 ? "standard-near" : "standard-above"}>{fmt(selectedRisk, 0)}</strong></div><div><span>Gap to Peak</span><strong>{fmt(selectedGap)}</strong></div>
            </div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">LAST FIVE RATING SHAPE</div><div className="last-five-rating-grid">{selectedL5.map((v, i) => <div key={`ls-${i}`}><span>{i + 1}LS</span><strong>{fmt(v)}</strong></div>)}</div></div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">JOCKEY INTELLIGENCE</div><div className="jockey-intel-grid"><div><span>Tier</span><strong><span className={`jockey-tier-pill ${tierClass(selected.jockeyTier)}`}>{safe(selected.jockeyTier || "UNKNOWN")}</span></strong></div><div><span>Recent Win</span><strong>{pct(selected.jockeyRecentWinSr)}</strong></div><div><span>Recent Place</span><strong>{pct(selected.jockeyRecentPlaceSr)}</strong></div><div><span>Actual v Expected</span><strong className={pointTone(selected.jockeyActualMinusExpected ?? null)}>{signed(selected.jockeyActualMinusExpected, 2)}</strong></div><div><span>ROI Last 100</span><strong className={pointTone(selected.jockeyRoiLast100 ?? null)}>{roi(selected.jockeyRoiLast100)}</strong></div><div><span>Best Track</span><strong>{safe(selected.jockeyBestTrack)}</strong></div><div><span>Best Distance</span><strong>{safe(selected.jockeyBestDistanceBand)}</strong></div><div><span>Best Combo</span><strong>{safe(selected.jockeyBestTrainerCombo)}</strong></div><div><span>Stat Adj</span><strong className={pointTone(selected.jockeyStatRatingPoints ?? null)}>{signed(selected.jockeyStatRatingPoints)}</strong></div><div><span>Manual Adj</span><strong className={pointTone(selected.manualJockeyAdjPoints ?? null)}>{signed(selected.manualJockeyAdjPoints)}</strong></div><div><span>Final Jockey Adj</span><strong className={pointTone(selected.jockeyAdjPoints ?? null)}>{signed(selected.jockeyAdjPoints)}</strong></div></div>{selected.jockeyAdjLabel ? <div className="jockey-penalty-warning">Manual jockey override: {selected.jockeyAdjLabel}</div> : null}</div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">TRAINER INTELLIGENCE</div><div className="jockey-intel-grid"><div><span>Tier</span><strong><span className={`jockey-tier-pill ${tierClass(selected.trainerTier)}`}>{safe(selected.trainerTier || "UNKNOWN")}</span></strong></div><div><span>Recent Win</span><strong>{pct(selected.trainerRecentWinSr)}</strong></div><div><span>ROI Last 100</span><strong className={pointTone(selected.trainerRoiLast100 ?? null)}>{roi(selected.trainerRoiLast100)}</strong></div><div><span>Actual v Expected</span><strong className={pointTone(selected.trainerActualMinusExpected ?? null)}>{signed(selected.trainerActualMinusExpected, 2)}</strong></div><div><span>Best Track</span><strong>{safe(selected.trainerBestTrack)}</strong></div><div><span>Best Distance</span><strong>{safe(selected.trainerBestDistanceBand)}</strong></div><div><span>Best Condition</span><strong>{safe(selected.trainerBestCondition)}</strong></div><div><span>Best Class</span><strong>{safe(selected.trainerBestClassBand)}</strong></div><div><span>Trainer Adj</span><strong className={pointTone(selected.trainerAdjPoints ?? null)}>{signed(selected.trainerAdjPoints)}</strong></div><div><span>Combo</span><strong>{safe(selected.comboAdjLabel)}</strong></div><div><span>Combo Rides</span><strong>{fmt(selected.comboRides, 0)}</strong></div><div><span>Combo Win</span><strong>{pct(selected.comboWinSr)}</strong></div><div><span>Combo ROI</span><strong className={pointTone(selected.comboRoi ?? null)}>{roi(selected.comboRoi)}</strong></div><div><span>Combo Adj</span><strong className={pointTone(selected.comboAdjPoints ?? null)}>{signed(selected.comboAdjPoints)}</strong></div><div><span>Total Connections</span><strong className={pointTone(selected.totalConnectionsAdj ?? null)}>{signed(selected.totalConnectionsAdj)}</strong></div></div></div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">HANDICAPPER LAYER</div><div className="rating-adjustment-stack handicapper-stack"><div><span>Before</span><strong>{fmt(selected.eliteTodayRatingBeforeHandicapper)}</strong></div><div><span>Trip Adj</span><strong className={pointTone(selected.tripAdjPoints ?? null)}>{signed(selected.tripAdjPoints)}</strong></div><div><span>Weight Adj</span><strong className={pointTone(selected.weightAdjPoints ?? null)}>{signed(selected.weightAdjPoints)}</strong></div><div><span>Jockey Adj</span><strong className={pointTone(selected.jockeyAdjPoints ?? null)}>{signed(selected.jockeyAdjPoints)}</strong></div><div><span>Total</span><strong className={pointTone(selected.handicapperAdjTotal ?? null)}>{signed(selected.handicapperAdjTotal)}</strong></div><div><span>Final</span><strong>{fmt(selected.handicapperRating ?? selected.todayRating)}</strong></div></div>{(selected.jockeyAdjPoints ?? 0) < 0 ? <div className="jockey-penalty-warning">Jockey penalty applied{selected.jockeyAdjLabel ? `: ${selected.jockeyAdjLabel}` : ""}</div> : null}</div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">PRICE DISCIPLINE</div><div className="rating-adjustment-stack handicapper-stack"><div><span>Raw</span><strong>{fmt(selected.rawEliteTodayRating)}</strong></div><div><span>Cal Adj</span><strong className={pointTone(selected.calibrationAdjPoints ?? null)}>{signed(selected.calibrationAdjPoints)}</strong></div><div><span>Calibrated</span><strong>{fmt(selected.calibratedTodayRating ?? selected.todayRating)}</strong></div><div><span>Confidence</span><strong>{safe(selected.priceConfidenceBand || "UNKNOWN")} {fmt(selected.modelConfidenceScore, 0)}</strong></div><div><span>Risk</span><strong>{safe(selected.fakeOverlayRisk || "UNKNOWN")}</strong></div><div><span>Label</span><strong>{safe(selected.calibrationLabel || "UNCHANGED")}</strong></div></div>{selected.fakeOverlayReason ? <div className="jockey-penalty-warning">Calibration: {selected.fakeOverlayReason}</div> : null}</div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">ADJUSTMENT STACK</div><div className="rating-adjustment-stack"><div><span>Class</span><strong>{adj(selected.classAdj)}</strong></div><div><span>Distance</span><strong>{adj(selected.distanceAdj)}</strong></div><div><span>Speed</span><strong>{adj(selected.speedAdj)}</strong></div><div><span>Recency</span><strong>{adj(selected.recencyAdj)}</strong></div><div><span>Momentum</span><strong>{adj(selected.momentumAdj)}</strong></div></div></div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">PRIOR RUNS VS TODAY STANDARD</div><div className="standard-run-list">{selectedRuns.map((run) => { const diff = run.runRating === null ? null : run.runRating - standard; return <div key={run.id} className={standardTone(diff)}><span>{dateShort(run.runDate)} | {safe(run.track)} {run.distance ? `${run.distance}m` : ""}</span><strong>{fmt(run.runRating)} <em>{diff === null ? "" : signed(diff)}</em></strong><em>{safe(run.raceClass)}</em></div>; })}{!selectedRuns.length ? <div className="standard-none empty">No official form history.</div> : null}</div></div>
            <div className="edgeiq-rating-section"><div className="edgeiq-ws-kicker">CAREER FILTERS</div><div className="edgeiq-career-grid"><div><span>Career</span><strong>{careerStats ? `${careerStats.careerStarts}: ${careerStats.careerWins}-${careerStats.careerSeconds}-${careerStats.careerThirds}` : "-"}</strong></div><div><span>Track</span><strong>{careerStats ? `${careerStats.trackStarts}: ${careerStats.trackWins}-${careerStats.trackSeconds}-${careerStats.trackThirds}` : "-"}</strong></div><div><span>Distance</span><strong>{careerStats ? `${careerStats.distanceStarts}: ${careerStats.distanceWins}-${careerStats.distanceSeconds}-${careerStats.distanceThirds}` : "-"}</strong></div></div></div>
          </> : <div className="edgeiq-muted">No runner selected.</div>}
        </aside>
      </div>
    </div>
  );
}






