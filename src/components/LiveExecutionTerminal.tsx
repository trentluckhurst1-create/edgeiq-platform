import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import { EDGEIQ_REFRESH_MS, EDGEIQ_LIVE_FILES } from "../config/edgeiqLiveFeeds";

type CsvRow = Record<string, string>;
type Tone = "good" | "warn" | "bad" | "neutral";

const FILES = {
  terminal: EDGEIQ_LIVE_FILES.terminalFeed,
  truth: "/data/edgeiq_market_truth_engine_v3.csv",
  suppression: "/data/edgeiq_execution_suppression_v2.csv",
  clv: "/data/edgeiq_clv_memory.csv",
  raceState: "/data/edgeiq_race_state_engine.csv",
};

function text(value: unknown): string {
  return String(value ?? "").trim();
}

function clean(value: unknown): string {
  const out = text(value);
  return out && out !== "-" && out.toUpperCase() !== "NAN" ? out : "";
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function num(value: unknown): number | null {
  const raw = clean(value).replace(/[$,%]/g, "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function first(row: CsvRow | undefined, keys: string[]): string {
  if (!row) return "";
  for (const key of keys) {
    if (clean(row[key])) return clean(row[key]);
  }
  return "";
}

function firstNum(row: CsvRow | undefined, keys: string[]): number | null {
  if (!row) return null;
  for (const key of keys) {
    const value = num(row[key]);
    if (value !== null) return value;
  }
  return null;
}

function price(value: unknown): string {
  const n = num(value);
  return n === null || n <= 0 ? "" : `$${n.toFixed(2)}`;
}

function pct(value: unknown): string {
  const n = num(value);
  return n === null ? "" : `${n.toFixed(1)}%`;
}

function cleanTrack(value: unknown): string {
  return clean(value)
    .toUpperCase()
    .replace(/BET365|SPORTSBET|LADBROKES|TAB|RACING|MRC|VRC/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function horseKey(value: unknown): string {
  return clean(value)
    .toUpperCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\([^)]*\)/g, "")
    .replace(/\b(NZ|AUS|IRE|GB|USA|FR|JPN|SAF|GER|CAN)\b/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

function key(track: unknown, raceNo: unknown, horse?: unknown): string {
  const race = num(raceNo) ?? 0;
  return `${cleanTrack(track)}|${race}${horse === undefined ? "" : `|${horseKey(horse)}`}`;
}

async function loadCsv(path: string): Promise<CsvRow[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const csv = await response.text();
    return Papa.parse<CsvRow>(csv, { header: true, skipEmptyLines: true }).data ?? [];
  } catch {
    return [];
  }
}

function lookup(rows: CsvRow[], includeHorse: boolean): Map<string, CsvRow> {
  const map = new Map<string, CsvRow>();
  rows.forEach((row) => map.set(key(row.track, row.race_no, includeHorse ? row.horse || row.horse_key : undefined), row));
  return map;
}

function tone(value: unknown): Tone {
  const v = upper(value);
  if (v.includes("ALLOW") || v.includes("VALID") || v.includes("HIGH") || v.includes("TRUST")) return "good";
  if (v.includes("KILL") || v.includes("SUPPRESS") || v.includes("REJECT") || v.includes("INVALID") || v.includes("LOW") || v.includes("DEAD")) return "bad";
  if (v.includes("REDUCE") || v.includes("MONITOR") || v.includes("QUESTION") || v.includes("MEDIUM") || v.includes("DRIFT")) return "warn";
  return "neutral";
}

function toneClass(value: Tone): string {
  if (value === "good") return "positive";
  if (value === "warn") return "warning";
  if (value === "bad") return "negative";
  return "neutral";
}

export default function LiveExecutionTerminal({ rows }: { rows: CsvRow[] }) {
  const [terminalRows, setTerminalRows] = useState<CsvRow[]>(rows || []);
  const [truthRows, setTruthRows] = useState<CsvRow[]>([]);
  const [suppressionRows, setSuppressionRows] = useState<CsvRow[]>([]);
  const [clvRows, setClvRows] = useState<CsvRow[]>([]);
  const [raceStateRows, setRaceStateRows] = useState<CsvRow[]>([]);
  const [updatedAt, setUpdatedAt] = useState("");

  useEffect(() => {
    let alive = true;
    async function load(): Promise<void> {
      const [terminal, truth, suppression, clv, raceState] = await Promise.all([
        rows?.length ? Promise.resolve(rows) : loadCsv(FILES.terminal),
        loadCsv(FILES.truth),
        loadCsv(FILES.suppression),
        loadCsv(FILES.clv),
        loadCsv(FILES.raceState),
      ]);
      if (!alive) return;
      setTerminalRows(terminal || []);
      setTruthRows(truth);
      setSuppressionRows(suppression);
      setClvRows(clv);
      setRaceStateRows(raceState);
      setUpdatedAt(new Date().toLocaleTimeString());
    }
    load();
    const timer = window.setInterval(load, EDGEIQ_REFRESH_MS || 15000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [rows]);

  const enriched = useMemo(() => {
    const truthMap = lookup(truthRows, true);
    const suppressionMap = lookup(suppressionRows, true);
    const clvMap = lookup(clvRows, true);
    const raceStateMap = lookup(raceStateRows, false);

    return terminalRows
      .map((row) => {
        const horse = first(row, ["horse", "runner", "runner_name", "selection_name"]);
        const track = first(row, ["track", "track_name", "meeting"]);
        const raceNo = first(row, ["race_no", "race_number", "race"]);
        const runnerKey = key(track, raceNo, horse);
        const raceKey = key(track, raceNo);
        const truth = truthMap.get(runnerKey);
        const suppression = suppressionMap.get(runnerKey);
        const clv = clvMap.get(runnerKey);
        const state = raceStateMap.get(raceKey);
        const action = clean(suppression?.suppression_action) || first(row, ["ui_action", "execution_action", "policy_decision", "final_action_v5_1"]) || "MONITOR";
        return {
          horse,
          track,
          raceNo,
          action,
          truth: clean(truth?.truth_grade),
          trust: num(truth?.execution_trust_score),
          confidence: clean(truth?.market_confidence),
          liquidity: clean(truth?.liquidity_grade),
          fakeOverlay: clean(truth?.fake_overlay_flag),
          driftRisk: clean(truth?.late_drift_risk),
          reason: clean(suppression?.suppression_reason) || clean(truth?.suppression_reason) || first(row, ["risk_flags", "policy_reason", "v2_reason"]),
          live: firstNum(row, ["ui_price", "sportsbet_price", "market_price", "live_price"]),
          fair: firstNum(row, ["ui_fair_price", "rated_price", "fair_price", "model_price"]),
          edge: firstNum(row, ["ui_edge_pct", "overlay_pct", "edge_pct"]),
          clv: clean(clv?.clv_achieved_pct),
          driftProfile: clean(clv?.runner_drift_profile),
          raceState: clean(state?.race_state),
          minutes: num(state?.minutes_to_jump),
          jockey: first(row, ["jockey"]),
          trainer: first(row, ["trainer"]),
          silk: first(row, ["mobile_silk_image", "silk_url", "silkUrl"]),
        };
      })
      .filter((row) => row.horse && row.track)
      .sort((a, b) => {
        const rank: Record<string, number> = { ALLOW: 0, REDUCE: 1, MONITOR: 2, KILL: 7, SUPPRESS: 8 };
        const ar = rank[upper(a.action)] ?? 4;
        const br = rank[upper(b.action)] ?? 4;
        if (ar !== br) return ar - br;
        return (b.trust ?? -1) - (a.trust ?? -1) || (b.edge ?? -999) - (a.edge ?? -999);
      });
  }, [terminalRows, truthRows, suppressionRows, clvRows, raceStateRows]);

  const summary = useMemo(() => {
    const allow = enriched.filter((row) => upper(row.action) === "ALLOW").length;
    const rejected = enriched.filter((row) => ["KILL", "SUPPRESS"].includes(upper(row.action))).length;
    const reduce = enriched.filter((row) => upper(row.action) === "REDUCE").length;
    const monitor = enriched.filter((row) => upper(row.action) === "MONITOR").length;
    return { allow, rejected, reduce, monitor };
  }, [enriched]);

  return (
    <section className="terminal-card">
      <div className="terminal-card-head">
        <div>
          <div className="terminal-kicker">Execution Discipline</div>
          <div className="terminal-muted">truth grade · suppression action · CLV memory · race state</div>
        </div>
        <div className="terminal-muted text-right">
          Updated <strong className="terminal-text">{updatedAt || "-"}</strong>
        </div>
      </div>

      <div className="terminal-grid four">
        <Metric label="Allow" value={summary.allow} tone="good" />
        <Metric label="Reduce" value={summary.reduce} tone="warn" />
        <Metric label="Monitor" value={summary.monitor} />
        <Metric label="Rejected" value={summary.rejected} tone="bad" />
      </div>

      <div className="terminal-table-wrap max-h-[430px]">
        <table className="terminal-table min-w-[1180px]">
          <thead>
            <tr>
              <th>#</th>
              <th>Runner</th>
              <th>Action</th>
              <th>Truth</th>
              <th className="num">Live</th>
              <th className="num">Fair</th>
              <th className="num">Edge</th>
              <th className="num">Trust</th>
              <th>Liquidity</th>
              <th>CLV</th>
              <th>State</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {enriched.length ? enriched.map((row, index) => (
              <tr key={`${row.track}-${row.raceNo}-${row.horse}-${index}`} className="border-b border-white/5 hover:bg-white/5">
                <td className="terminal-faint">{index + 1}</td>
                <td>
                  <div className="flex items-center gap-3">
                    {row.silk ? <img src={row.silk} className="h-7 w-7 rounded border border-white/10 object-contain" alt="" /> : <div className="h-7 w-7 rounded border border-white/10 bg-slate-800" />}
                    <div className="min-w-0">
                      <div className="truncate font-bold text-white">{row.horse}</div>
                      <div className="terminal-meta terminal-faint">{row.track} R{row.raceNo}</div>
                    </div>
                  </div>
                </td>
                <td><Badge value={row.action} tone={tone(row.action)} /></td>
                <td><Badge value={row.truth || "PENDING"} tone={tone(row.truth)} /></td>
                <td className="num">{price(row.live)}</td>
                <td className="num">{price(row.fair)}</td>
                <td className={`num ${(row.edge ?? 0) >= 7 ? "terminal-positive" : (row.edge ?? 0) < 0 ? "terminal-negative" : "terminal-muted"}`}>{pct(row.edge)}</td>
                <td className="num">{row.trust === null ? "" : row.trust.toFixed(0)}</td>
                <td>{row.liquidity}</td>
                <td>{row.clv ? `${row.clv}%` : row.driftProfile}</td>
                <td>{row.raceState}{row.minutes !== null ? <div className="terminal-meta terminal-faint">{row.minutes.toFixed(1)}m</div> : null}</td>
                <td className="max-w-[360px] truncate terminal-muted" title={row.reason}>{row.reason}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={12}><div className="terminal-empty">
                  NO LIVE EXECUTION DISCIPLINE DATA
                </div></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Badge({ value, tone }: { value: string; tone: Tone }) {
  return <span className={`terminal-chip ${toneClass(tone)}`}>{value || ""}</span>;
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: number; tone?: Tone }) {
  const color = tone === "good" ? "terminal-positive" : tone === "bad" ? "terminal-negative" : tone === "warn" ? "terminal-warning" : "terminal-text";
  return (
    <div className={`terminal-metric ${tone}`}>
      <span>{label}</span>
      <div className={`text-[18px] font-black leading-tight ${color}`}>{value}</div>
    </div>
  );
}



