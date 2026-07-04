import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type Row = Record<string, string>;

function num(v: string | undefined): number {
  const x = Number(v);
  return Number.isFinite(x) ? x : 0;
}

function money(v: string | undefined): string {
  const x = Number(v);
  return Number.isFinite(x) && x > 0 ? x.toFixed(2) : "-";
}

function edge(v: string | undefined): string {
  const x = Number(v);
  return Number.isFinite(x) ? `${x > 0 ? "+" : ""}${x.toFixed(1)}%` : "-";
}

function pct(v: string | undefined): string {
  const x = Number(v);
  return Number.isFinite(x) ? `${x.toFixed(1)}%` : "-";
}

function units(v: string | undefined): string {
  const x = Number(v);
  return Number.isFinite(x) ? x.toFixed(2) : "-";
}

function signalTone(signal?: string): string {
  const s = String(signal || "").toUpperCase();
  if (s === "STEAMER" || s === "FIRMING") return "terminal-positive";
  if (s === "DRIFTER" || s === "BIG DRIFTER") return "text-red-300";
  return "terminal-muted";
}

function actionTone(action?: string): string {
  const s = String(action || "").toUpperCase();
  if (s === "BET") return "positive";
  if (s === "WATCH") return "border-amber-400/40 bg-amber-400/10 text-amber-200";
  if (s === "WIN") return "positive";
  if (s === "LOSS") return "border-red-400/40 bg-red-400/10 text-red-200";
  return "neutral";
}

function movementDisplay(row: Row): string {
  const open = num(row.opening_price);
  const current = num(row.current_price || row.market_price_clean);
  const previous = num(row.previous_price);
  const from = open && current && open !== current ? open : previous;
  return from && current ? `${from.toFixed(2)} -> ${current.toFixed(2)}` : row.fluc_display || "-";
}

function movementChange(row: Row): string {
  const openPct = num(row.move_from_open_pct);
  const tickPct = num(row.price_delta_pct);
  const pctValue = Math.abs(openPct) > 0.05 ? openPct : tickPct;
  const signal = String(row.market_signal || "STABLE").toUpperCase();
  return `${signal} ${pctValue >= 0 ? "+" : ""}${pctValue.toFixed(1)}%`;
}

async function loadCsv(path: string): Promise<Row[]> {
  try {
    const res = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) return [];
    const text = await res.text();
    return Papa.parse<Row>(text, { header: true, skipEmptyLines: true }).data;
  } catch {
    return [];
  }
}

export default function LiveBetsTab() {
  const [rows, setRows] = useState<Row[]>([]);
  const [paperRows, setPaperRows] = useState<Row[]>([]);
  const [settledRows, setSettledRows] = useState<Row[]>([]);
  const [summaryRows, setSummaryRows] = useState<Row[]>([]);
  const [updated, setUpdated] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      const [live, paper, settled, summary] = await Promise.all([
        loadCsv("/data/edgeiq_live_bets.csv"),
        loadCsv("/data/paper_bets.csv"),
        loadCsv("/data/paper_bets_settled.csv"),
        loadCsv("/data/bet_review_summary.csv"),
      ]);
      if (!active) return;
      setRows(live);
      setPaperRows(paper);
      setSettledRows(settled);
      setSummaryRows(summary);
      setUpdated(new Date().toLocaleTimeString());
    }
    load().catch(() => {});
    const timer = window.setInterval(() => { load().catch(() => {}); }, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const displayRows = useMemo(() => rows.filter((r) => r.action_grade === "BET" || r.action_grade === "WATCH").sort((a, b) => num(b.overlay_score) - num(a.overlay_score)), [rows]);
  const openPaper = useMemo(() => settledRows.filter((r) => String(r.status || "").toUpperCase() === "OPEN").sort((a, b) => `${a.race_date}${a.track}${a.race_no}`.localeCompare(`${b.race_date}${b.track}${b.race_no}`)), [settledRows]);
  const recentSettled = useMemo(() => settledRows.filter((r) => ["WIN", "LOSS"].includes(String(r.status || "").toUpperCase())).slice(-40).reverse(), [settledRows]);
  const overall = useMemo(() => summaryRows.find((r) => r.segment_type === "OVERALL") ?? null, [summaryRows]);
  const byConfidence = useMemo(() => summaryRows.filter((r) => r.segment_type === "CONFIDENCE"), [summaryRows]);

  return (
    <div className="space-y-3">
      <div className="terminal-card terminal-stack">
        <div className="mb-3 flex items-end justify-between">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.25em] text-[#6ee7b7]">EDGEiQ RACING</div>
            <h2 className="m-0 text-[20px] font-bold text-white">Bets / Paper Validation</h2>
            <p className="terminal-muted m-0 mt-1">Paper tracking only. No real-money execution. Treat ROI as validation sample, not proven profitability.</p>
          </div>
          <div className="terminal-chip neutral">Updated {updated || "-"}</div>
        </div>

        <div className="grid gap-2 md:grid-cols-4 lg:grid-cols-7">
          <div className="terminal-metric neutral"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">Paper Bets</span><strong className="mt-1 block text-xl text-white">{overall?.total_bets ?? paperRows.length}</strong></div>
          <div className="terminal-metric neutral"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">Open</span><strong className="mt-1 block text-xl text-white">{overall?.open_bets ?? openPaper.length}</strong></div>
          <div className="terminal-metric neutral"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">Settled</span><strong className="mt-1 block text-xl text-white">{overall?.settled_bets ?? "0"}</strong></div>
          <div className="terminal-metric neutral"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">Wins</span><strong className="mt-1 block text-xl text-white">{overall?.wins ?? "0"}</strong></div>
          <div className="terminal-metric neutral"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">Strike</span><strong className="mt-1 block text-xl text-white">{pct(overall?.strike_rate)}</strong></div>
          <div className="terminal-metric neutral"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">Units</span><strong className="mt-1 block text-xl text-white">{units(overall?.profit_units)}</strong></div>
          <div className="terminal-metric neutral"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">CLV</span><strong className="mt-1 block text-xl text-white">{pct(overall?.avg_clv)}</strong></div>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
        <div className="terminal-card terminal-stack">
          <div className="mb-2 flex items-end justify-between">
            <div><div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#6ee7b7]">PAPER BET LOG</div><h3 className="m-0 text-[16px] font-bold text-white">Open Paper Bets</h3></div>
            <span className="terminal-muted terminal-meta">{openPaper.length} open</span>
          </div>
          <div className="terminal-table-wrap max-h-[360px]">
            <table className="min-w-full table-fixed text-[12px]">
              <colgroup><col className="w-[130px]" /><col className="w-[220px]" /><col className="w-[72px]" /><col className="w-[82px]" /><col className="w-[82px]" /><col className="w-[82px]" /><col className="w-[110px]" /><col className="w-[100px]" /></colgroup>
              <thead className="terminal-table-head"><tr><th className="px-3 py-2 text-left">Race</th><th className="px-3 py-2 text-left">Horse</th><th className="px-3 py-2 text-right">Rank</th><th className="px-3 py-2 text-right">Rated</th><th className="px-3 py-2 text-right">Market</th><th className="px-3 py-2 text-right">Stake</th><th className="px-3 py-2 text-center">Action</th><th className="px-3 py-2 text-right">Signal</th></tr></thead>
              <tbody>{openPaper.map((r, i) => <tr key={`${r.bet_id}-${i}`} className="terminal-table-row"><td className="terminal-cell terminal-text whitespace-nowrap">{r.track} R{r.race_no}</td><td className="terminal-cell terminal-strong truncate">{r.horse}</td><td className="px-3 py-2 text-right text-slate-300">{r.rated_rank || "-"}</td><td className="px-3 py-2 text-right text-slate-300">{money(r.rated_price)}</td><td className="px-3 py-2 text-right font-bold text-white">{money(r.market_price)}</td><td className="px-3 py-2 text-right text-slate-300">{units(r.stake_units)}</td><td className="px-3 py-2 text-center"><span className={`terminal-chip ${actionTone(r.action_grade)}`}>{r.action_grade}</span></td><td className={`px-3 py-2 text-right font-bold ${signalTone(r.market_signal)}`}>{r.market_signal || "-"}</td></tr>)}{!openPaper.length && <tr><td colSpan={8} className="terminal-empty-state">No open paper bets logged.</td></tr>}</tbody>
            </table>
          </div>
        </div>

        <div className="terminal-card terminal-stack">
          <div className="mb-2"><div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#6ee7b7]">VALIDATION SPLITS</div><h3 className="m-0 text-[16px] font-bold text-white">By Confidence</h3></div>
          <div className="space-y-2">{byConfidence.map((r) => <div key={r.segment} className="terminal-list-row"><strong className="text-white">{r.segment}</strong><span className="text-right text-slate-400">{r.total_bets} bets</span><span className="text-right text-slate-400">{r.settled_bets} set</span><span className="text-right text-slate-300">{pct(r.roi_pct)}</span></div>)}{!byConfidence.length && <div className="terminal-empty-state">Awaiting confidence samples.</div>}</div>
        </div>
      </div>

      <div className="terminal-card terminal-stack">
        <div className="mb-2 flex items-end justify-between">
          <div><div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#6ee7b7]">SETTLED PAPER RESULTS</div><h3 className="m-0 text-[16px] font-bold text-white">Recent Settled Bets</h3></div>
          <span className="terminal-muted terminal-meta">{recentSettled.length} shown</span>
        </div>
        <div className="terminal-table-wrap">
          <table className="min-w-full table-fixed text-[12px]">
            <colgroup><col className="w-[130px]" /><col className="w-[220px]" /><col className="w-[80px]" /><col className="w-[80px]" /><col className="w-[80px]" /><col className="w-[80px]" /><col className="w-[80px]" /><col className="w-[90px]" /></colgroup>
            <thead className="terminal-table-head"><tr><th className="px-3 py-2 text-left">Race</th><th className="px-3 py-2 text-left">Horse</th><th className="px-3 py-2 text-right">Market</th><th className="px-3 py-2 text-right">SP</th><th className="px-3 py-2 text-right">Finish</th><th className="px-3 py-2 text-right">P/L</th><th className="px-3 py-2 text-right">CLV</th><th className="px-3 py-2 text-center">Status</th></tr></thead>
            <tbody>{recentSettled.map((r, i) => <tr key={`${r.bet_id}-settled-${i}`} className="terminal-table-row"><td className="terminal-cell terminal-text whitespace-nowrap">{r.track} R{r.race_no}</td><td className="terminal-cell terminal-strong truncate">{r.horse}</td><td className="px-3 py-2 text-right text-slate-300">{money(r.market_price)}</td><td className="px-3 py-2 text-right text-slate-300">{money(r.result_sp)}</td><td className="px-3 py-2 text-right text-slate-300">{r.finish_pos || "-"}</td><td className="px-3 py-2 text-right font-bold text-white">{units(r.profit_units)}</td><td className="px-3 py-2 text-right text-slate-300">{pct(r.clv_pct)}</td><td className="px-3 py-2 text-center"><span className={`terminal-chip ${actionTone(r.status)}`}>{r.status}</span></td></tr>)}{!recentSettled.length && <tr><td colSpan={8} className="terminal-empty-state">No settled paper bets yet. Results will populate after official outcomes are collected.</td></tr>}</tbody>
          </table>
        </div>
      </div>

      <div className="terminal-card terminal-stack">
        <div className="mb-3 flex items-end justify-between">
          <div><div className="text-[10px] font-bold uppercase tracking-[0.25em] text-[#6ee7b7]">EDGEiQ RACING</div><h2 className="m-0 text-[20px] font-bold text-white">Live Bets / Market Signals</h2></div>
        </div>
        <div className="terminal-table-wrap">
          <table className="min-w-full table-fixed text-[12px]">
            <colgroup><col className="w-[140px]" /><col className="w-[220px]" /><col className="w-[90px]" /><col className="w-[90px]" /><col className="w-[150px]" /><col className="w-[150px]" /><col className="w-[90px]" /><col className="w-[90px]" /></colgroup>
            <thead className="terminal-table-head"><tr><th className="px-3 py-2 text-left">Race</th><th className="px-3 py-2 text-left">Horse</th><th className="px-3 py-2 text-right">Rated</th><th className="px-3 py-2 text-right">Market</th><th className="px-3 py-2 text-right">Move</th><th className="px-3 py-2 text-right">Signal</th><th className="px-3 py-2 text-right">Edge</th><th className="px-3 py-2 text-center">Action</th></tr></thead>
            <tbody>{displayRows.map((r, i) => {
              const moveClass = signalTone(r.market_signal);
              return <tr key={`${r.track}-${r.race_no}-${r.horse}-${i}`} className="terminal-table-row"><td className="terminal-cell terminal-text whitespace-nowrap">{r.track} R{r.race_no}</td><td className="terminal-cell terminal-strong truncate">{r.horse}</td><td className="px-3 py-2 text-right text-slate-300">{money(r.elite_rated_price)}</td><td className="px-3 py-2 text-right font-bold text-white">{money(r.market_price_clean || r.current_price)}</td><td className={`px-3 py-2 text-right font-bold ${moveClass}`}>{movementDisplay(r)}</td><td className={`px-3 py-2 text-right font-bold ${moveClass}`}>{movementChange(r)}</td><td className="px-3 py-2 text-right text-slate-200">{edge(r.edge_pct)}</td><td className="px-3 py-2 text-center"><span className={`terminal-chip ${actionTone(r.action_grade)}`}>{r.action_grade}</span></td></tr>;
            })}{!displayRows.length && <tr><td colSpan={8} className="terminal-empty-state">No live BET / WATCH runners found.</td></tr>}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

