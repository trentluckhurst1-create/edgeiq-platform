import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type CsvRow = Record<string, string>;
type Tone = "good" | "warn" | "bad" | "neutral";

const FILES = {
  truthLoop: "/data/edgeiq_results_truth_loop.csv",
  accountability: "/data/edgeiq_execution_accountability.csv",
  tape: "/data/edgeiq_market_tape_summary.csv",
  clv: "/data/edgeiq_clv_memory.csv",
  health: "/data/edgeiq_pipeline_health.csv",
};

function clean(value: unknown): string {
  const output = String(value ?? "").trim();
  return output && output !== "-" && output.toUpperCase() !== "NAN" ? output : "";
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function num(value: unknown): number {
  const parsed = Number(clean(value).replace(/[$,%]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function money(value: unknown): string {
  return `$${num(value).toFixed(2)}`;
}

function pct(value: unknown): string {
  return clean(value) ? `${num(value).toFixed(1)}%` : "-";
}

function toneFrom(value: unknown): Tone {
  const status = upper(value);
  if (status.includes("GOOD") || status.includes("WON") || status.includes("OK") || status.includes("SETTLED")) return "good";
  if (status.includes("FAIL") || status.includes("LOST") || status.includes("POOR")) return "bad";
  if (status.includes("PENDING") || status.includes("WARN") || status.includes("REVIEW")) return "warn";
  return "neutral";
}

function toneClass(value: Tone): string {
  if (value === "good") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (value === "warn") return "bg-amber-500/15 text-amber-300 border-amber-500/30";
  if (value === "bad") return "bg-rose-500/15 text-rose-300 border-rose-500/30";
  return "bg-slate-500/10 text-slate-300 border-slate-500/20";
}

async function readCsv(path: string): Promise<CsvRow[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const csv = await response.text();
    return Papa.parse<CsvRow>(csv, { header: true, skipEmptyLines: true }).data ?? [];
  } catch {
    return [];
  }
}

export default function SettlementCentre(): React.ReactElement {
  const [truthRows, setTruthRows] = useState<CsvRow[]>([]);
  const [accountRows, setAccountRows] = useState<CsvRow[]>([]);
  const [tapeRows, setTapeRows] = useState<CsvRow[]>([]);
  const [clvRows, setClvRows] = useState<CsvRow[]>([]);
  const [healthRows, setHealthRows] = useState<CsvRow[]>([]);
  const [loadedAt, setLoadedAt] = useState("");

  useEffect(() => {
    let alive = true;

    async function load(): Promise<void> {
      const [truthLoop, accountability, tape, clv, health] = await Promise.all([
        readCsv(FILES.truthLoop),
        readCsv(FILES.accountability),
        readCsv(FILES.tape),
        readCsv(FILES.clv),
        readCsv(FILES.health),
      ]);

      if (!alive) return;

      setTruthRows(truthLoop);
      setAccountRows(accountability);
      setTapeRows(tape);
      setClvRows(clv);
      setHealthRows(health);
      setLoadedAt(new Date().toLocaleTimeString());
    }

    load();
    const timer = window.setInterval(load, 60000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const summary = useMemo(() => {
    const pending = truthRows.filter((row) => upper(row.result_status) === "PENDING").length;
    const settled = truthRows.length - pending;
    const pnl = truthRows.reduce((sum, row) => sum + num(row.pnl), 0);
    const turnover = truthRows.reduce((sum, row) => sum + num(row.stake), 0);
    const positiveClv = truthRows.filter((row) => clean(row.clv_result) && num(row.clv_result) >= 0).length;
    const warnings = healthRows.filter((row) => ["WARN", "FAIL"].includes(upper(row.status))).length;
    return {
      pending,
      settled,
      pnl,
      roi: turnover ? (pnl / turnover) * 100 : 0,
      positiveClv,
      warnings,
    };
  }, [healthRows, truthRows]);

  const reviewRows = useMemo(() => {
    return [...truthRows]
      .sort((a, b) => {
        if (upper(a.result_status) === "PENDING" && upper(b.result_status) !== "PENDING") return -1;
        if (upper(a.result_status) !== "PENDING" && upper(b.result_status) === "PENDING") return 1;
        return Math.abs(num(b.pnl)) - Math.abs(num(a.pnl));
      })
      .slice(0, 12);
  }, [truthRows]);

  const warnings = useMemo(
    () => healthRows.filter((row) => ["WARN", "FAIL"].includes(upper(row.status))).slice(0, 6),
    [healthRows],
  );

  const truthMessage = summary.pending === truthRows.length && truthRows.length > 0
    ? "All current truth-loop rows are still pending official settlement."
    : summary.settled > 0
      ? "Settled truth is available. Accountability and CLV context are live."
      : "Settlement truth has not populated yet.";

  return (
    <div className="edgeiq-settlement-centre">
      <div className="edgeiq-settlement-hero">
        <div>
          <div className="edgeiq-kicker">RESULTS</div>
          <h1>Execution Accountability</h1>
          <p>
            Settlement is driven by the truth loop, market tape memory and CLV memory. Pending rows stay visible until official results arrive.
          </p>
        </div>
        <div className="edgeiq-heartbeat">
          <span className="pulse-dot" />
          ACCOUNTABILITY POLL
          <strong>{loadedAt || "LOADING"}</strong>
        </div>
      </div>

      <div className="edgeiq-terminal-banner">
        <strong>Truth status</strong>
        <span>{truthMessage}</span>
      </div>

      <div className="grid gap-3 md:grid-cols-5">
        <Stat label="Pending" value={summary.pending} tone="warn" sub="awaiting official result" />
        <Stat label="Settled" value={summary.settled} tone={summary.settled ? "good" : "neutral"} sub="truth-loop rows" />
        <Stat label="P/L" value={money(summary.pnl)} tone={summary.pnl >= 0 ? "good" : "bad"} sub={`${summary.roi.toFixed(1)}% ROI`} />
        <Stat label="Positive CLV" value={summary.positiveClv} tone="good" sub="tracked rows" />
        <Stat label="Warnings" value={summary.warnings} tone={summary.warnings ? "warn" : "neutral"} sub="pipeline health" />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.1fr_1.2fr_0.9fr]">
        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">ACCOUNTABILITY SUMMARY</div>
          <div className="edgeiq-settlement-table">
            {accountRows.length ? accountRows.map((row) => (
              <div className="edgeiq-settlement-row" key={clean(row.decision_group)}>
                <span className="rank">{clean(row.decision_group)}</span>
                <span className="horse">{clean(row.summary) || clean(row.decision_group)}</span>
                <span>{clean(row.pending) || "0"} pending</span>
                <span>{clean(row.settled) || "0"} settled</span>
                <span>{money(row.pnl)}</span>
                <strong className={toneClass(toneFrom(row.accountability_grade))}>{clean(row.accountability_grade) || "PENDING"}</strong>
              </div>
            )) : <div className="edgeiq-empty-state">No accountability rows generated yet.</div>}
          </div>
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">RESULTS TRUTH LOOP</div>
          <div className="edgeiq-settlement-table">
            {reviewRows.length ? reviewRows.map((row, index) => (
              <div className="edgeiq-settlement-row" key={`${clean(row.track)}-${clean(row.race_no)}-${clean(row.horse)}-${index}`}>
                <span className="rank">{index + 1}</span>
                <span className="horse">{clean(row.horse)}</span>
                <span>{clean(row.track)} R{clean(row.race_no)}</span>
                <span>{clean(row.execution_decision) || "OBSERVE"}</span>
                <span><Badge value={clean(row.result_status) || "PENDING"} tone={toneFrom(row.result_status)} /></span>
                <strong>{money(row.pnl)} | CLV {pct(row.clv_result)}</strong>
              </div>
            )) : <div className="edgeiq-empty-state">No results truth rows generated yet.</div>}
          </div>
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">MARKET CONTEXT</div>
          <div className="grid gap-2">
            <ContextCard label="Tape summary rows" value={String(tapeRows.length)} detail="price memory available" tone={tapeRows.length ? "good" : "warn"} />
            <ContextCard label="CLV memory rows" value={String(clvRows.length)} detail="open / mid / close archive" tone={clvRows.length ? "good" : "warn"} />
            <ContextCard label="Pending bias" value={`${summary.pending}/${truthRows.length || 0}`} detail="pending / total truth rows" tone={summary.pending ? "warn" : "neutral"} />
            <div className="edgeiq-panel-title">HEALTH WARNINGS</div>
            <div className="edgeiq-settlement-table">
              {warnings.length ? warnings.map((row, index) => (
                <div className="edgeiq-settlement-row" key={`${clean(row.check_name)}-${index}`}>
                  <span className="rank">{index + 1}</span>
                  <span className="horse">{clean(row.check_name)}</span>
                  <span>{clean(row.file)}</span>
                  <span>{clean(row.status)}</span>
                  <span>{clean(row.rows)} rows</span>
                  <strong>{clean(row.message)}</strong>
                </div>
              )) : <div className="edgeiq-empty-state">No system health warnings.</div>}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function Badge({ value, tone }: { value: string; tone: Tone }): React.ReactElement {
  return (
    <span className={`inline-flex rounded-md border px-2 py-1 text-[9px] font-black uppercase tracking-[0.12em] ${toneClass(tone)}`}>
      {value}
    </span>
  );
}

function Stat({
  label,
  value,
  tone,
  sub,
}: {
  label: string;
  value: string | number;
  tone: Tone;
  sub: string;
}): React.ReactElement {
  const valueClass = tone === "good" ? "emerald" : tone === "bad" ? "red" : tone === "warn" ? "gold" : "blue";
  return (
    <div className="edgeiq-stat-card">
      <div className="label">{label}</div>
      <div className={`value ${valueClass}`}>{value}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}

function ContextCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
}): React.ReactElement {
  return (
    <div className="rounded-xl border border-slate-700 bg-[#08131c] px-3 py-3">
      <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className={`mt-1 text-[18px] font-black ${tone === "good" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : tone === "bad" ? "text-rose-300" : "text-white"}`}>
        {value}
      </div>
      <div className="mt-1 text-[10px] text-slate-400">{detail}</div>
    </div>
  );
}
