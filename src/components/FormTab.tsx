import React, { useMemo } from "react";
import type {
  CareerStats,
  FormHistoryRow,
  FormSummary,
  FullCareerFormRow,
  RatingDisplayRow,
} from "../App";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  selectedHorseHistory?: FormHistoryRow[];
  selectedFullCareer?: FullCareerFormRow[];
  selectedSummary?: FormSummary | null;
  selectedCareerStats?: CareerStats | null;
  speedRows?: Record<string, any>[];
};

type RawRow = Record<string, any>;
type Kpi = { label: string; value: string; tone?: string };
type StartRow = {
  date: string;
  track: string;
  distance: string;
  raceClass: string;
  condition: string;
  finish: string;
  margin: string;
  jockey: string;
  sp: string;
  rating: string;
  comment: string;
};

const EMPTY = new Set(["", "-", "NA", "N/A", "NULL", "NONE", "NAN", "UNDEFINED", "UNKNOWN"]);

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  return EMPTY.has(text.toUpperCase()) ? "" : text;
}

function has(value: unknown): boolean {
  const text = clean(value);
  return Boolean(text && /[A-Za-z0-9]/.test(text.replace(/[-/|:.,\s]/g, "")));
}

function num(value: unknown): number | null {
  const parsed = Number(String(value ?? "").replace(/[$,%]/g, "").trim());
  return Number.isFinite(parsed) ? parsed : null;
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    if (has(value)) return clean(value);
  }
  return "";
}

function pick(row: RawRow | null | undefined, keys: string[]): unknown {
  if (!row) return "";
  for (const key of keys) {
    const value = row[key];
    if (has(value)) return value;
  }
  return "";
}

function compact(items: Kpi[]): Kpi[] {
  return items.filter((item) => has(item.value));
}

function canon(value: unknown): string {
  return String(value ?? "").toUpperCase().replace(/\([^)]*\)/g, "").replace(/[^A-Z0-9]/g, "");
}

function selectedRow(rows: RatingDisplayRow[], selectedHorseKey: string): RatingDisplayRow | null {
  return rows.find((row) => row.horseKey === selectedHorseKey) ?? rows.find((row) => !row.isScratched) ?? rows[0] ?? null;
}

function fmtPrice(value: unknown): string {
  const n = num(value);
  if (n === null || n <= 0) return "";
  return n >= 100 ? n.toFixed(0) : n.toFixed(2).replace(/\.00$/, "");
}

function fmtRating(value: unknown): string {
  const n = num(value);
  return n === null ? "" : n.toFixed(1).replace(/\.0$/, "");
}

function fmtDays(value: unknown): string {
  const text = clean(value);
  if (!text) return "";
  return text.toLowerCase().includes("day") || text.endsWith("d") ? text : `${text}d`;
}

function dateShort(value: unknown): string {
  const raw = clean(value);
  if (!raw) return "";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "2-digit" });
}

function distanceText(value: unknown): string {
  const text = clean(value);
  if (!text) return "";
  return text.endsWith("m") ? text : `${text}m`;
}

function record(starts?: unknown, wins?: unknown, seconds?: unknown, thirds?: unknown): string {
  const s = num(starts) ?? 0;
  if (!s) return "";
  return `${s}-${num(wins) ?? 0}-${num(seconds) ?? 0}-${num(thirds) ?? 0}`;
}

function wetRecord(stats: RawRow | null | undefined): string {
  const starts = (num(stats?.softStarts) ?? 0) + (num(stats?.heavyStarts) ?? 0);
  if (!starts) return "";
  return `${starts}-${(num(stats?.softWins) ?? 0) + (num(stats?.heavyWins) ?? 0)}-${(num(stats?.softSeconds) ?? 0) + (num(stats?.heavySeconds) ?? 0)}-${(num(stats?.softThirds) ?? 0) + (num(stats?.heavyThirds) ?? 0)}`;
}

function runDateValue(row: RawRow): number {
  return new Date(row.runDate ?? row.date ?? row.race_date ?? row.meetingDate ?? 0).getTime();
}

function isRaceRun(row: RawRow): boolean {
  const runType = clean(row.runType ?? row.run_type ?? row.type).toUpperCase();
  if (!runType) return row.isOfficialRace !== false;
  return runType === "RACE" || runType === "OFFICIAL" || Boolean(row.isOfficialRace);
}

function runRating(row: RawRow): string {
  return firstText(row.ratingDisplay, fmtRating(row.runRating), fmtRating(row.rating), fmtRating(row.performance_rating), fmtRating(row.final_rating), fmtRating(row.todayRating));
}

function runComment(row: RawRow): string {
  return firstText(
    row.comments,
    row.comment,
    row.stewards,
    row.stewards_comment,
    row.sectional_comment,
    row.sectional,
    row.sectional_profile,
    row.in_run,
    row.in_run_comment,
    row.race_comment
  );
}

function startRows(history: RawRow[], career: RawRow[]): StartRow[] {
  const source = (career.length ? career : history)
    .filter(isRaceRun)
    .sort((a, b) => runDateValue(b) - runDateValue(a))
    .slice(0, 5);

  return source.map((run) => ({
    date: dateShort(run.runDate ?? run.date ?? run.race_date ?? run.meetingDate),
    track: firstText(run.track, run.venue),
    distance: distanceText(run.distance),
    raceClass: firstText(run.raceClass, run.class, run.grade, run.race_class),
    condition: firstText(run.trackCondition, run.condition, run.going, run.track_condition),
    finish: firstText(run.finishPos, run.finish, run.position, run.result),
    margin: firstText(run.margin, run.beatenMargin, run.beaten_margin),
    jockey: firstText(run.jockey, run.rider),
    sp: fmtPrice(firstText(run.sp, run.startingPrice, run.starting_price, run.fixed_sp)),
    rating: runRating(run),
    comment: runComment(run),
  }));
}

function formString(summary: RawRow | null | undefined, runner: RawRow | null | undefined): string {
  const direct = firstText(runner?.form_string, runner?.last_5, runner?.last5, runner?.recent_form, runner?.horse_form, summary?.form_string, summary?.last5);
  if (direct) return direct;
  const values = [summary?.ls1, summary?.ls2, summary?.ls3, summary?.ls4, summary?.ls5].filter(has);
  return values.join("-");
}

function classMove(row: RawRow | null | undefined, summary: RawRow | null | undefined): string {
  return firstText(row?.class_movement, row?.class_move, row?.class_change, row?.grade_movement, row?.race_class_move, summary?.class_movement, summary?.classMove);
}

export default function FormTab({
  runners,
  selectedHorseKey,
  selectedHorseHistory = [],
  selectedFullCareer = [],
  selectedSummary = null,
  selectedCareerStats = null,
  speedRows = [],
}: Props): React.ReactElement {
  const selected = selectedRow(runners, selectedHorseKey) as RawRow | null;
  const stats = selectedCareerStats as RawRow | null;
  const summary = selectedSummary as RawRow | null;
  const selectedSpeed = speedRows.find((row) => canon(row.horse ?? row.horse_name ?? row.runner_name) === canon(selected?.horse));
  const official = useMemo(() => startRows(selectedHorseHistory as RawRow[], selectedFullCareer as RawRow[]), [selectedHorseHistory, selectedFullCareer]);

  const formKpis = compact([
    { label: "Last 5", value: formString(summary, selected) },
    { label: "Avg Last 3", value: fmtRating(firstText(summary?.avg3, summary?.last3Avg, selected?.avg3, selected?.last3Avg)) },
    { label: "Avg Last 5", value: fmtRating(firstText(summary?.avg5, summary?.last5Avg, selected?.avg5, selected?.last5Avg)) },
    { label: "Peak Rating", value: fmtRating(firstText(summary?.peak, summary?.peakRating, selected?.peak, selected?.peakRating)) },
    { label: "Days Since", value: fmtDays(firstText(summary?.gap, summary?.daysSinceRun, selected?.days_since_run, selected?.daysSinceRun)) },
    { label: "Class Move", value: classMove(selected, summary) },
  ]);

  const recordKpis = compact([
    { label: "Career", value: record(stats?.careerStarts, stats?.careerWins, stats?.careerSeconds, stats?.careerThirds) },
    { label: "Track", value: record(stats?.trackStarts, stats?.trackWins, stats?.trackSeconds, stats?.trackThirds) },
    { label: "Distance", value: record(stats?.distanceStarts, stats?.distanceWins, stats?.distanceSeconds, stats?.distanceThirds) },
    { label: "Track/Dist", value: record(stats?.trackDistanceStarts, stats?.trackDistanceWins, stats?.trackDistanceSeconds, stats?.trackDistanceThirds) },
    { label: "Wet", value: wetRecord(stats) },
    { label: "First Up", value: record(stats?.firstUpStarts, stats?.firstUpWins, stats?.firstUpSeconds, stats?.firstUpThirds) },
    { label: "Second Up", value: record(stats?.secondUpStarts, stats?.secondUpWins, stats?.secondUpSeconds, stats?.secondUpThirds) },
  ]);

  const tacticalKpis = compact([
    { label: "Settling", value: firstText(selectedSpeed?.settling_position, selectedSpeed?.settling_band, selectedSpeed?.map_position, selected?.map_position) },
    { label: "Run Style", value: firstText(selectedSpeed?.run_style, selectedSpeed?.archetype, selected?.run_style_cluster, selected?.sectional_profile) },
    { label: "Tempo Fit", value: firstText(selectedSpeed?.tempo_fit, selectedSpeed?.tempo_fit_v2, selected?.tempo_fit, selected?.tempo_fit_v2) },
    { label: "Pace Score", value: fmtRating(firstText(selectedSpeed?.early_speed, selectedSpeed?.projected_spd, selectedSpeed?.pace_score)) },
  ]);

  return (
    <section className="edgeiq-form-guide-tab">
      {formKpis.length ? <KpiSection title="Form Snapshot" items={formKpis} /> : null}
      {recordKpis.length ? <KpiSection title="Records" items={recordKpis} /> : null}
      {tacticalKpis.length ? <KpiSection title="Map Profile" items={tacticalKpis} /> : null}

      {official.length ? (
        <section className="deep-form-section">
          <div className="deep-form-section-title">Last 5 Starts</div>
          <div className="deep-form-table">
            <div className="deep-form-row deep-form-head">
              <span>Date</span>
              <span>Track</span>
              <span>Dist</span>
              <span>Class</span>
              <span>Cond</span>
              <span>Fin</span>
              <span>Mgn</span>
              <span>Jockey</span>
              <span>SP</span>
              <span>Rating</span>
              <span>Comment / Sectional</span>
            </div>
            {official.map((run, index) => (
              <div className="deep-form-row" key={`${run.date}-${run.track}-${index}`}>
                <span>{run.date}</span>
                <span>{run.track}</span>
                <span>{run.distance}</span>
                <span>{run.raceClass}</span>
                <span>{run.condition}</span>
                <span>{run.finish}</span>
                <span>{run.margin}</span>
                <span>{run.jockey}</span>
                <span>{run.sp}</span>
                <span>{run.rating}</span>
                <span>{run.comment}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}

function KpiSection({ title, items }: { title: string; items: Kpi[] }): React.ReactElement | null {
  const filtered = compact(items);
  if (!filtered.length) return null;
  return (
    <section className="deep-form-section">
      <div className="deep-form-section-title">{title}</div>
      <div className="deep-form-kpi-grid">
        {filtered.map((item) => <div className={`deep-form-kpi ${item.tone ?? ""}`} key={`${title}-${item.label}-${item.value}`}><span>{item.label}</span><strong>{item.value}</strong></div>)}
      </div>
    </section>
  );
}
