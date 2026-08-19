import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

const DATA = "/data/";

const keyOf = (r) => [
  r.race_date,
  String(r.track || "").toUpperCase().replace(/[^A-Z0-9]/g, ""),
  String(r.race_no || "").replace(/[^0-9]/g, ""),
  String(r.horse || "").toUpperCase().replace(/[^A-Z0-9]/g, ""),
].join("|");

async function loadCsv(name) {
  try {
    const res = await fetch(DATA + name + "?v=" + Date.now(), { cache: "no-store" });
    if (!res.ok) return [];
    const text = await res.text();
    const parsed = Papa.parse(text, {
      header: true,
      dynamicTyping: false,
      skipEmptyLines: true,
    });
    return Array.isArray(parsed.data) ? parsed.data : [];
  } catch {
    return [];
  }
}

const fmt = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(2) : v || "-";
};


const cell = (r, keys, fallback = "-") => {
  for (const k of keys) {
    if (r && r[k] !== undefined && r[k] !== null && String(r[k]).trim() !== "") return r[k];
  }
  return fallback;
};

const intFmt = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? String(Math.round(n)) : v || "-";
};

function badgeClass(kind, value) {
  const v = String(value || "").toUpperCase();

  if (kind === "instruction") {
    if (v === "NO_BET") return "border-red-500/30 bg-red-500/10 text-red-300";
    if (v.includes("EXECUTE")) return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
    return "border-zinc-700 bg-zinc-900 text-zinc-300";
  }

  if (kind === "tier") {
    if (v === "ELITE") return "border-cyan-400/40 bg-cyan-400/10 text-cyan-200";
    if (v === "STRONG") return "border-emerald-400/40 bg-emerald-400/10 text-emerald-200";
    if (v === "ACTIONABLE") return "border-lime-400/30 bg-lime-400/10 text-lime-200";
    return "border-zinc-700 bg-zinc-900 text-zinc-300";
  }

  if (kind === "signal") {
    if (v === "FIRMING") return "border-emerald-400/40 bg-emerald-400/10 text-emerald-200";
    if (v === "STABLE") return "border-cyan-400/30 bg-cyan-400/10 text-cyan-200";
    return "border-zinc-700 bg-zinc-900 text-zinc-300";
  }

  return "border-zinc-700 bg-zinc-900 text-zinc-300";
}

export default function ExecutionLearningTab() {
  const [summary, setSummary] = useState([]);
  const [qualified, setQualified] = useState([]);
  const [suppressed, setSuppressed] = useState([]);
  const [byTrack, setByTrack] = useState([]);
  const [adaptiveFeed, setAdaptiveFeed] = useState([]);
  const [adaptiveSummary, setAdaptiveSummary] = useState([]);
  const [regime, setRegime] = useState([]);
  const [suppressionReasons, setSuppressionReasons] = useState([]);
  const [liveStatus, setLiveStatus] = useState([]);
  const [marketMovers, setMarketMovers] = useState([]);

  useEffect(() => {

    const loadAll = () =>
      Promise.all([
      loadCsv("edgeiq_execution_feed_v1_summary.csv"),
      loadCsv("edgeiq_execution_feed_v1.csv"),
      loadCsv("edgeiq_execution_suppressed_v1.csv"),
      loadCsv("edgeiq_live_filter_v1_by_track.csv"),
      loadCsv("edgeiq_adaptive_staking_v1.csv"),
      loadCsv("edgeiq_adaptive_staking_summary_v1.csv"),
      loadCsv("edgeiq_market_regime_v1.csv"),
      loadCsv("edgeiq_execution_suppression_reasons_v1.csv"),
      loadCsv("edgeiq_live_orchestrator_status.csv"),
    ]).then(([s, q, r, t, stake, stakeSummary, reg, reasons, live]) => {
      setSummary(s || []);
      setQualified(q || []);
      setSuppressed(r || []);
      setByTrack(t || []);
      setAdaptiveFeed(stake || []);
      setAdaptiveSummary(stakeSummary || []);
      setRegime(reg || []);
      setSuppressionReasons(reasons || []);
      setLiveStatus(live || []);
    });

    loadAll();

    const loadMovers = () =>
      loadCsv("edgeiq_paper_market_movers_v1.csv").then((rows) => {
        setMarketMovers(Array.isArray(rows) ? rows : []);
      });

    loadMovers();

    const interval = setInterval(() => {
      loadAll();
      loadMovers();
    }, 15000);

    return () => clearInterval(interval);

  }, []);

  const s = summary[0] || {};
  const reg = regime[0] || {};
  const live =
    Array.isArray(liveStatus) && liveStatus.length
      ? liveStatus[0]
      : {};

  const liveCycle =
    live["cycle_no"] ||
    live["CYCLE_NO"] ||
    "-";

  const liveMemory =
    live["memory_rows"] ||
    live["MEMORY_ROWS"] ||
    "-";

  const liveOkRaw =
    live["scripts_ok"] ||
    live["SCRIPTS_OK"] ||
    false;

  const liveOk =
    String(liveOkRaw).toLowerCase().includes("true")
      ? "OK"
      : "CHECK";

  const stakeSummaryRows = adaptiveSummary || [];

  const topRows = useMemo(() => {
    const stakeByKey = new Map(
      adaptiveFeed.map((r) => [
        keyOf(r),
        r,
      ])
    );

    return [...qualified]
      .map((r) => ({
        ...r,
        ...(stakeByKey.get(keyOf(r)) || {}),
      }))
      .sort((a, b) => Number(b.execution_score || 0) - Number(a.execution_score || 0))
      .slice(0, 50);
  }, [qualified, adaptiveFeed]);

  const totalStake = useMemo(() => {
    return adaptiveFeed.reduce((sum, r) => sum + (Number(r.adaptive_stake_units) || 0), 0);
  }, [adaptiveFeed]);

  const executeCount = useMemo(() => {
    return adaptiveFeed.filter((r) => String(r.execution_instruction || "").toUpperCase() !== "NO_BET").length;
  }, [adaptiveFeed]);

  return (
    <div className="edgeiq-aux-terminal text-zinc-100">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.35em] text-emerald-400">
            EDGEiQ RACING
          </div>
          <h1 className="text-2xl font-black tracking-tight">
            Execution Learning Filter
          </h1>
          <p className="text-sm text-zinc-400">
            Suppression → scoring → CLV → regime → adaptive staking.
          </p>
        </div>

        <div className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-200">
          LIVE CYCLE {liveCycle} · {liveOk} · MEMORY {liveMemory}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-9">
        {[
          ["Qualified", s.qualified],
          ["Rejected", s.rejected],
          ["Screened", s.screened],
          ["Qual Rate", `${fmt(s.qualification_rate_pct)}%`],
          ["Avg Score", fmt(s.avg_execution_score)],
          ["Avg Edge", `${fmt(s.avg_edge_pct)}%`],
          ["Avg Market", fmt(s.avg_market_price)],
          ["Execute", executeCount],
          ["Stake Units", fmt(totalStake)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-3 shadow-lg">
            <div className="text-[10px] uppercase tracking-[0.25em] text-zinc-500">
              {k}
            </div>
            <div className="mt-1 text-xl font-black text-zinc-100">
              {v ?? "-"}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-400/5 p-4">
        <div className="text-[10px] uppercase tracking-[0.28em] text-amber-300">
          Regime Note
        </div>
        <div className="mt-1 text-sm font-bold text-amber-100">
          {reg.mode_note || "No regime note loaded."}
        </div>
        <div className="mt-2 text-xs text-zinc-400">
          CLV: {fmt(reg.avg_clv_pct)}% · Beat close: {fmt(reg.beat_closing_line_pct)}% · Bad CLV: {intFmt(reg.bad_clv_count)}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 shadow-xl">
          <div className="border-b border-zinc-800 px-4 py-3">
            <div className="text-sm font-black uppercase tracking-[0.22em] text-emerald-300">
              Adaptive Execution Feed V1
            </div>
            <div className="text-xs text-zinc-500">
              Qualified runners with CLV, regime mode, stake size, and execution instruction.
            </div>
          </div>

          <div className="overflow-auto">
            <table className="w-full min-w-[1320px] text-left text-xs">
              <thead className="bg-zinc-950/90 text-[10px] uppercase tracking-[0.22em] text-zinc-500">
                <tr>
                  <th className="px-3 py-2">Track</th>
                  <th className="px-3 py-2">Race</th>
                  <th className="px-3 py-2">Horse</th>
                  <th className="px-3 py-2">Tier</th>
                  <th className="px-3 py-2 text-right">Score</th>
                  <th className="px-3 py-2">Signal</th>
                  <th className="px-3 py-2">Risk</th>
                  <th className="px-3 py-2">Calib</th>
                  <th className="px-3 py-2 text-right">Edge</th>
                  <th className="px-3 py-2 text-right">Market</th>
                  <th className="px-3 py-2 text-right">Rated</th>
                  <th className="px-3 py-2 text-right">CLV</th>
                  <th className="px-3 py-2 text-right">Stake</th>
                  <th className="px-3 py-2">Instruction</th>
                  <th className="px-3 py-2">Why</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-zinc-900 text-[12px]">
                {topRows.map((r, idx) => (
                  <tr key={`${r.track}-${r.race_no}-${r.horse}-${idx}`} className="hover:bg-emerald-500/5">
                    <td className="px-3 py-2 font-bold text-white">{r.track}</td>
                    <td className="px-3 py-2 text-zinc-400">R{r.race_no}</td>
                    <td className="px-3 py-2 font-black text-white">{r.horse}</td>

                    <td className="px-3 py-2">
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-black ${badgeClass("tier", r.execution_tier)}`}>
                        {r.execution_tier || "-"}
                      </span>
                    </td>

                    <td className="px-3 py-2 text-right font-black text-white">{fmt(r.execution_score)}</td>

                    <td className="px-3 py-2">
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-black ${badgeClass("signal", r.market_signal)}`}>
                        {r.market_signal || "-"}
                      </span>
                    </td>

                    <td className="px-3 py-2 text-zinc-300">{r.fake_overlay_risk || "-"}</td>
                    <td className="px-3 py-2 text-zinc-300">{r.calibration_label || "-"}</td>
                    <td className="px-3 py-2 text-right font-black text-emerald-300">{fmt(r.edge_pct)}%</td>
                    <td className="px-3 py-2 text-right text-zinc-300">{fmt(r.market_price)}</td>
                    <td className="px-3 py-2 text-right text-zinc-400">{fmt(r.rated_price)}</td>

                    <td className={[
                      "px-3 py-2 text-right font-black",
                      Number(r.clv_pct || 0) > 0
                        ? "text-emerald-300"
                        : Number(r.clv_pct || 0) < 0
                        ? "text-red-300"
                        : "text-zinc-500"
                    ].join(" ")}>
                      {fmt(r.clv_pct)}%
                    </td>

                    <td className="px-3 py-2 text-right font-black text-cyan-300">
                      {fmt(r.adaptive_stake_units)}
                    </td>

                    <td className="px-3 py-2">
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-black ${badgeClass("instruction", r.execution_instruction)}`}>
                        {r.execution_instruction || "-"}
                      </span>
                    </td>

                    <td className="max-w-[260px] px-3 py-2 text-[10px] leading-snug text-zinc-500">
                      {r.why_qualified || "-"}
                    </td>
                  </tr>
                ))}

                {!topRows.length && (
                  <tr>
                    <td className="px-4 py-8 text-center text-zinc-500" colSpan="15">
                      No execution feed rows found. Run build_edgeiq_execution_feed_v1.py and build_edgeiq_adaptive_staking_v1.py.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 shadow-xl">
            <div className="border-b border-zinc-800 px-4 py-3">
              <div className="text-sm font-black uppercase tracking-[0.22em] text-emerald-300">
                Qualified By Track
              </div>
            </div>
            <div className="p-3">
              {byTrack.slice(0, 14).map((r) => (
                <div key={r.track} className="mb-2 flex items-center justify-between rounded-xl border border-zinc-900 bg-black/30 px-3 py-2">
                  <span className="text-xs font-bold text-zinc-200">{r.track}</span>
                  <span className="rounded-full bg-emerald-400/10 px-2 py-1 text-xs font-black text-emerald-300">
                    {r.qualified_bets}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-cyan-500/20 bg-cyan-950/10 p-4 shadow-xl">
            <div className="text-sm font-black uppercase tracking-[0.22em] text-cyan-300">
              Adaptive Staking
            </div>
            <div className="mt-3 space-y-2">
              {stakeSummaryRows.map((r, idx) => (
                <div key={idx} className="rounded-xl border border-cyan-900/30 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-black text-cyan-200">{r.execution_instruction}</div>
                  <div className="mt-1 text-zinc-400">
                    runners {r.runners} · stake {fmt(r.total_stake)} · score {fmt(r.avg_score)} · CLV {fmt(r.avg_clv)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-950/10 p-4 shadow-xl">
            <div className="text-sm font-black uppercase tracking-[0.22em] text-emerald-300">
              Market Movers
            </div>
            <div className="mt-3 space-y-2">
              {marketMovers
                .filter((r) => cell(r, ["horse", "Horse", "HORSE"], "") !== "")
                .slice(0, 10)
                .map((r, idx) => {
                  const horse = cell(r, ["horse", "Horse", "HORSE"]);
                  const track = cell(r, ["track", "Track", "TRACK"]);
                  const raceNo = cell(r, ["race_no", "race", "Race", "RACE_NO"]);
                  const firstPrice = cell(r, ["first_price", "open_price", "First Price"]);
                  const latestPrice = cell(r, ["latest_price", "Latest Price"]);
                  const movePct = cell(r, ["move_pct", "Move %"], "0");
                  const moveType = cell(r, ["move_type", "Move Type"]);
                  const read = cell(r, ["market_read", "Market Read"]);

                  return (
                    <div key={idx} className="rounded-xl border border-emerald-900/30 bg-black/20 px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-black text-zinc-100">{horse}</div>
                        <div className={Number(movePct || 0) >= 0 ? "font-black text-emerald-300" : "font-black text-red-300"}>
                          {fmt(movePct)}%
                        </div>
                      </div>
                      <div className="mt-1 text-[11px] text-zinc-400">
                        {track} R{raceNo} · {firstPrice} → {latestPrice} · {moveType}
                      </div>
                      <div className="mt-1 text-[10px] font-bold text-amber-300">
                        {read}
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>

          <div className="rounded-2xl border border-red-500/20 bg-red-950/10 p-4 shadow-xl">
            <div className="text-sm font-black uppercase tracking-[0.22em] text-red-300">
              Top Suppression Reasons
            </div>
            <div className="mt-3 space-y-2">
              {suppressionReasons.slice(0, 8).map((r, idx) => (
                <div key={idx} className="flex items-center justify-between rounded-lg border border-red-900/30 bg-black/20 px-2 py-2 text-[10px]">
                  <div className="pr-3 text-zinc-300">{r.edgeiq_suppression_reason_v1}</div>
                  <div className="font-black text-red-300">{r.rows}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-zinc-500">
              Current rejected rows: <b className="text-red-200">{suppressed.length}</b>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

