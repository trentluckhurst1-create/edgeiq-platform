import { useEffect, useMemo, useState } from "react";

type Row = Record<string, any>;
type Run = {
  horse: string;
  key: string;
  rating: number;
  date: string;
  track: string;
  raceNo: string;
  distance: string;
  raceClass: string;
  trackCondition: string;
  finishPos: string;
  margin: string;
  fieldSize: string;
  jockey: string;
  sp: string;
  winner: string;
  runType: string;
  flags: string;
};
type RunnerMeta = { key: string; horse: string; horseNo: number | null; today: number | null; peak: number | null; avg3: number | null; avg5: number | null; silkUrl: string; scratched: boolean };
type HorseSeries = RunnerMeta & { runs: Array<Run | null>; trend: number | null; latest: number | null };
type Props = { data?: Row[]; runners?: Row[]; selectedHorse?: string; selectedHorseKey?: string; onSelectHorse?: (horseKey: string) => void; [key: string]: any };

function val(row: Row | undefined, keys: string[]): string {
  for (const k of keys) {
    const v = row?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== "") return String(v).trim();
  }
  return "";
}

function clean(x: any): string {
  return String(x ?? "").toUpperCase().normalize("NFKD").replace(/[^\x00-\x7F]/g, "").replace(/\([^)]*\)/g, " ").replace(/[‘’'`]/g, "").replace(/[^A-Z0-9]/g, "");
}

function safe(v: unknown): string {
  const s = String(v ?? "").trim();
  if (!s || s.toLowerCase() === "nan" || s.toLowerCase() === "null") return "-";
  return s;
}

function num(x: any): number | null {
  const n = Number(String(x ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function parseCsv(text: string): Row[] {
  const lines = text.replace(/\r/g, "").split("\n").filter(Boolean);
  if (!lines.length) return [];
  const split = (line: string) => {
    const out: string[] = [];
    let cur = "";
    let quoted = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      const next = line[i + 1];
      if (ch === '"' && quoted && next === '"') { cur += '"'; i++; }
      else if (ch === '"') quoted = !quoted;
      else if (ch === "," && !quoted) { out.push(cur); cur = ""; }
      else cur += ch;
    }
    out.push(cur);
    return out;
  };
  const headers = split(lines[0]).map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const cells = split(line);
    const row: Row = {};
    headers.forEach((h, i) => { row[h] = cells[i] ?? ""; });
    return row;
  });
}

function collectFlags(row: Row): string {
  const text = ["stewards", "stewards_report", "comments", "comment", "run_notes", "notes", "gear_changes", "gear_change", "in_run_positions"].map((k) => val(row, [k])).join(" ").toLowerCase();
  const flags = ["held up", "checked", "wide", "slow", "vet", "gear"].filter((flag) => text.includes(flag));
  return flags.length ? flags.join(" | ").toUpperCase() : "Insufficient run context";
}

function mapRun(row: Row): Run | null {
  const horse = val(row, ["horse", "Horse", "runner", "Runner", "horse_name", "runner_name", "name"]);
  const key = clean(val(row, ["horseKey", "horse_key", "matchKey", "match_key"]) || horse);
  const rating = num(val(row, ["runRating", "run_rating", "rating", "Rating", "todayRating", "today_rating", "rated"]));
  const runTypeRaw = val(row, ["runType", "run_type", "type"]);
  const runType = clean(runTypeRaw) || "RACE";
  const officialRaw = clean(val(row, ["isOfficialRace", "is_official_race", "official"]));
  if (!horse || !key || rating === null || rating <= 0 || runType.includes("TRIAL") || runType.includes("JUMP")) return null;
  if (officialRaw && ["FALSE", "0", "NO"].includes(officialRaw)) return null;
  return {
    horse,
    key,
    rating,
    date: val(row, ["runDate", "run_date", "date", "Date"]),
    track: val(row, ["track", "Track"]),
    raceNo: val(row, ["raceNo", "race_no", "race", "race_number"]),
    distance: val(row, ["distance", "Distance"]),
    raceClass: val(row, ["raceClass", "race_class", "class", "Class"]),
    trackCondition: val(row, ["trackCondition", "track_condition", "condition"]),
    finishPos: val(row, ["finishPos", "finish_pos", "placing", "place"]),
    margin: val(row, ["margin", "margin_beaten"]),
    fieldSize: val(row, ["fieldSize", "field_size", "starters", "field"]),
    jockey: val(row, ["jockey", "Jockey"]),
    sp: val(row, ["sp", "SP", "starting_price", "sp_text"]),
    winner: val(row, ["winner", "Winner"]),
    runType: runTypeRaw || "RACE",
    flags: collectFlags(row),
  };
}

function avg(xs: number[]): number | null {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
}

function fmt(x: number | null | undefined, digits = 1): string {
  return x === null || x === undefined || !Number.isFinite(x) ? "-" : x.toFixed(digits);
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

function resultLine(run: Run): string {
  const finish = safe(run.finishPos);
  const field = safe(run.fieldSize);
  const margin = safe(run.margin);
  const first = finish !== "-" ? `Finished ${ordinal(finish)}${field !== "-" ? ` of ${field}` : ""}` : "Finished position unavailable";
  return margin !== "-" ? `${first}, beaten ${margin}${/l$/i.test(margin) ? "" : "L"}` : first;
}

function ratingTone(rating: number | null, min: number, max: number): string {
  if (rating === null) return "none";
  const pct = (rating - min) / Math.max(max - min, 1);
  if (pct >= 0.78) return "top";
  if (pct >= 0.55) return "mid";
  return "low";
}

function runnerMeta(row: Row): RunnerMeta {
  const horse = val(row, ["horse", "Horse", "runner", "Runner"]);
  const key = clean(val(row, ["horseKey", "horse_key", "matchKey", "match_key"]) || horse);
  return {
    key,
    horse,
    horseNo: num(val(row, ["horseNo", "horse_no", "saddlecloth", "number", "No"])),
    today: num(val(row, ["todayRating", "today_rating", "elite_today_rating"])),
    peak: num(val(row, ["peak", "PEAK"])),
    avg3: num(val(row, ["recentSimpleAvg", "recent_simple_avg", "avg3", "3LSA"])),
    avg5: num(val(row, ["baseLast5", "base_last5", "avg5", "5LSA"])),
    silkUrl: val(row, ["silkUrl", "silk_url", "local_silk_path"]),
    scratched: ["1", "true", "yes", "y"].includes(String(val(row, ["isScratched", "is_scratched"])).trim().toLowerCase()),
  };
}

function sparkPath(values: Array<number | null>, min: number, max: number): string {
  const points = values.map((value, index) => {
    if (value === null) return null;
    const x = 8 + index * 21;
    const y = 28 - ((value - min) / Math.max(max - min, 1)) * 22;
    return `${x.toFixed(1)},${Math.max(4, Math.min(30, y)).toFixed(1)}`;
  }).filter(Boolean) as string[];
  return points.join(" ");
}

function RunTooltip({ run, value }: { run: Run | null; value: number | null }) {
  return (
    <span className="edgeiq-run-rating-hover perf-run-hover">
      <strong>{fmt(value)}</strong>
      <span className="edgeiq-run-tooltip" role="tooltip">
        {run ? (
          <>
            <span className="tooltip-kicker">{safe(run.runType) || "RACE"}</span>
            <strong>{safe(run.track)}{safe(run.raceNo) !== "-" ? ` R${safe(run.raceNo)}` : ""} | {safe(run.raceClass)} | {safe(run.distance) !== "-" ? `${safe(run.distance)}m` : "-"} | {safe(run.trackCondition)}</strong>
            <em>{dateShort(run.date)}</em>
            <span>{resultLine(run)}</span>
            <span>Jockey: {safe(run.jockey)} | SP: {safe(run.sp)}</span>
            <span>Winner: {safe(run.winner)} | Field: {safe(run.fieldSize)}</span>
            <span>Run rating: {fmt(run.rating)}</span>
            <span className="tooltip-flags">{run.flags}</span>
          </>
        ) : (
          <span>Insufficient run context</span>
        )}
      </span>
    </span>
  );
}

export default function PerformanceTab({ data = [], runners = [], selectedHorse, selectedHorseKey, onSelectHorse }: Props) {
  const [fallback, setFallback] = useState<Row[]>([]);
  const [mode, setMode] = useState<"ALL" | "CONTENDERS" | "SELECTED">("ALL");
  const [showScratched, setShowScratched] = useState(false);
  const [localSelectedKey, setLocalSelectedKey] = useState("");

  useEffect(() => {
    if (data.length) return;
    let alive = true;
    fetch("/data/full_career_form.csv", { cache: "no-store" }).then((r) => r.text()).then((t) => { if (alive) setFallback(parseCsv(t)); }).catch(() => {});
    return () => { alive = false; };
  }, [data.length]);

  const source = data.length ? data : fallback;
  const runnerMap = useMemo(() => {
    const map = new Map<string, RunnerMeta>();
    runners.forEach((row) => {
      const meta = runnerMeta(row);
      if (meta.key) map.set(meta.key, meta);
    });
    return map;
  }, [runners]);

  const series = useMemo<HorseSeries[]>(() => {
    const runMap = new Map<string, Run[]>();
    source.forEach((row) => {
      const run = mapRun(row);
      if (!run || (runnerMap.size && !runnerMap.has(run.key))) return;
      if (!runMap.has(run.key)) runMap.set(run.key, []);
      runMap.get(run.key)!.push(run);
    });

    const rows: HorseSeries[] = [];
    const keys = runnerMap.size ? Array.from(runnerMap.keys()) : Array.from(runMap.keys());
    keys.forEach((key) => {
      const meta = runnerMap.get(key) ?? { key, horse: runMap.get(key)?.[0]?.horse ?? key, horseNo: null, today: null, peak: null, avg3: null, avg5: null, silkUrl: "", scratched: false };
      const sortedRuns = [...(runMap.get(key) ?? [])].sort((a, b) => String(b.date).localeCompare(String(a.date))).slice(0, 5);
      const padded: Array<Run | null> = [...sortedRuns];
      while (padded.length < 5) padded.push(null);
      const ratings = padded.map((r) => r?.rating ?? null);
      const cleanRatings = ratings.filter((x): x is number => x !== null);
      const latest = ratings[0] ?? null;
      const previous = ratings[1] ?? null;
      rows.push({
        ...meta,
        runs: padded,
        latest,
        today: meta.today ?? latest,
        peak: meta.peak ?? (cleanRatings.length ? Math.max(...cleanRatings) : null),
        avg3: meta.avg3 ?? avg(cleanRatings.slice(0, 3)),
        avg5: meta.avg5 ?? avg(cleanRatings.slice(0, 5)),
        trend: latest !== null && previous !== null ? latest - previous : null,
      });
    });
    return rows.sort((a, b) => {
      if (a.scratched !== b.scratched) return a.scratched ? 1 : -1;
      const ah = a.horseNo ?? 9999;
      const bh = b.horseNo ?? 9999;
      if (ah !== bh) return ah - bh;
      return a.horse.localeCompare(b.horse);
    });
  }, [source, runnerMap]);

  useEffect(() => {
    const next = clean(selectedHorseKey || selectedHorse);
    if (next) setLocalSelectedKey(next);
    else if (!localSelectedKey && series[0]) setLocalSelectedKey(series[0].key);
  }, [selectedHorseKey, selectedHorse, series, localSelectedKey]);

  const active = series.find((h) => h.key === localSelectedKey) ?? series[0] ?? null;
  const contenders = new Set(series.filter((h) => !h.scratched).slice(0, 8).map((h) => h.key));
  const visible = series.filter((h) => (showScratched || !h.scratched) && (mode === "SELECTED" ? h.key === active?.key : mode === "CONTENDERS" ? contenders.has(h.key) || h.key === active?.key : true));
  const allRatings = visible.flatMap((h) => h.runs.map((r) => r?.rating ?? null).filter((x): x is number => x !== null));
  const minRating = Math.max(35, Math.floor(Math.min(...(allRatings.length ? allRatings : [55])) / 5) * 5 - 5);
  const maxRating = Math.ceil(Math.max(...(allRatings.length ? allRatings : [90])) / 5) * 5 + 5;

  function selectHorse(key: string): void {
    setLocalSelectedKey(key);
    onSelectHorse?.(key);
  }

  return (
    <section className="edgeiq-performance performance-board terminal-panel-stack">
      <div className="performance-head terminal-card performance-board-head">
        <div><div className="edgeiq-ws-kicker">EDGEiQ PERFORMANCE</div><div className="performance-sub">Last five official race ratings by saddlecloth order | hover ratings for run detail</div></div>
        <div className="performance-modes">{(["ALL", "CONTENDERS", "SELECTED"] as const).map((m) => <button key={m} onClick={() => setMode(m)} className={mode === m ? "active" : ""}>{m}</button>)}{series.some((h) => h.scratched) ? <button onClick={() => setShowScratched((v) => !v)} className={showScratched ? "active" : ""}>{showScratched ? "HIDE SCR" : `SHOW SCR (${series.filter((h) => h.scratched).length})`}</button> : null}</div>
      </div>

      <div className="performance-matrix-layout">
        <aside className="performance-side terminal-card performance-selected-panel">
          <div className="small-label">SELECTED PROFILE</div>
          <Metric label="Runner" value={active?.horse || "-"} />
          <Metric label="Today" value={fmt(active?.today)} />
          <Metric label="Peak" value={fmt(active?.peak)} />
          <Metric label="Avg 3" value={fmt(active?.avg3)} />
          <Metric label="Avg 5" value={fmt(active?.avg5)} />
          <Metric label="Trend" value={active?.trend === null || active?.trend === undefined ? "-" : `${active.trend >= 0 ? "+" : ""}${active.trend.toFixed(1)}`} />
          <div className="performance-scale"><span>{fmt(maxRating, 0)}</span><em>rating scale</em><span>{fmt(minRating, 0)}</span></div>
        </aside>

        <div className="terminal-card performance-matrix-card">
          <div className="performance-matrix-header"><span>Runner</span><span>5-run rating path</span><span>5LS</span><span>4LS</span><span>3LS</span><span>2LS</span><span>1LS</span><span>Today</span><span>Peak</span><span>Avg3</span><span>Avg5</span><span>Trend</span></div>
          <div className="performance-matrix-body">
            {visible.map((row) => {
              const activeRow = row.key === active?.key;
              const ratingsOldToNew = [...row.runs].reverse().map((r) => r?.rating ?? null);
              const ratingsDisplay = [...row.runs].reverse();
              return <button key={row.key} className={`performance-matrix-row ${activeRow ? "active" : ""} ${row.scratched ? "scratched" : ""}`} onClick={() => selectHorse(row.key)}>
                <span className="perf-runner-name"><em>{row.horseNo ?? "-"}</em><strong>{row.horse}</strong></span>
                <span className="perf-spark-wrap"><svg viewBox="0 0 100 34" className="perf-sparkline" preserveAspectRatio="none"><line x1="4" x2="96" y1="28" y2="28" /><line x1="4" x2="96" y1="16" y2="16" /><polyline points={sparkPath(ratingsOldToNew, minRating, maxRating)} />{ratingsOldToNew.map((value, pointIndex) => value === null ? null : <circle key={`${row.key}-pt-${pointIndex}`} cx={8 + pointIndex * 21} cy={Math.max(4, Math.min(30, 28 - ((value - minRating) / Math.max(maxRating - minRating, 1)) * 22))} r={activeRow ? 2.2 : 1.6} />)}</svg></span>
                {ratingsDisplay.map((run, i) => <span key={`${row.key}-r-${i}`} className={`perf-rating-cell ${ratingTone(run?.rating ?? null, minRating, maxRating)}`}><RunTooltip run={run} value={run?.rating ?? null} /></span>)}
                <span className="perf-rating-cell today">{fmt(row.today)}</span><span className="perf-rating-cell">{fmt(row.peak)}</span><span className="perf-rating-cell">{fmt(row.avg3)}</span><span className="perf-rating-cell">{fmt(row.avg5)}</span><span className={`perf-trend ${row.trend !== null && row.trend !== undefined && row.trend >= 0 ? "up" : "down"}`}>{row.trend === null || row.trend === undefined ? "-" : `${row.trend >= 0 ? "+" : ""}${row.trend.toFixed(1)}`}</span>
              </button>;
            })}
            {!visible.length ? <div className="performance-empty">Insufficient history for this race.</div> : null}
          </div>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="performance-metric"><span>{label}</span><strong>{value}</strong></div>;
}

