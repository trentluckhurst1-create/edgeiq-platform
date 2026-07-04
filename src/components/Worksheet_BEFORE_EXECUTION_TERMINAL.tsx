import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import type { FormHistoryRow, RatingDisplayRow } from "../App";
import { DEFAULT_SILK_URL, getSilksUrl, silkFallback } from "../utils/silks";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  selectedHorseHistory?: FormHistoryRow[];
};

type MarketSignalRow = {
  track?: string;
  race_no?: string;
  horse?: string;
  horse_key?: string;
  opening_price?: string;
  previous_price?: string;
  current_price?: string;
  price_delta?: string;
  price_delta_pct?: string;
  move_from_open_pct?: string;
  market_signal?: string;
  market_confidence?: string;
};

type SignalState = {
  display: string;
  change: string;
  signal: string;
  tone: "firming" | "drifting" | "stable" | "none";
};

function rating(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "-";
  return v.toFixed(1);
}

function price(v: number | null): string {
  if (v === null || !Number.isFinite(v) || v <= 0) return "-";
  return v.toFixed(2);
}

function pct(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "-";
  return `${Math.max(-99.9, Math.min(999.9, v)).toFixed(1)}%`;
}

function dateShort(d: string): string {
  const x = new Date(d);
  if (Number.isNaN(x.getTime())) return d || "-";
  return x.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "2-digit" });
}

function safe(v?: string | number | null): string {
  if (v === null || v === undefined || String(v).trim() === "") return "-";
  return String(v);
}

function n(v: unknown): number | null {
  const x = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(x) ? x : null;
}

function hardKey(v: unknown): string {
  return String(v ?? "")
    .toUpperCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\s*\([A-Z]+\)/g, "")
    .replace(/[’'`]/g, "")
    .replace(/[^A-Z0-9]/g, "")
    .trim();
}

function trackKey(v: unknown): string {
  return String(v ?? "").toUpperCase().replace(/[^A-Z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}

function signalKey(track: string, raceNo: string | number | null | undefined, horse: string, horseKey?: string): string {
  return `${trackKey(track)}|${String(raceNo || "").replace(/\.0$/, "").trim()}|${hardKey(horseKey || horse)}`;
}

function marketText(r: RatingDisplayRow): string {
  if (r.isScratched) return "SCR";
  return price(r.marketPrice);
}

function edgeTone(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "edgeiq-muted";
  if (v >= 15) return "edgeiq-green";
  if (v > 0) return "edgeiq-lime";
  return "edgeiq-red";
}

function conditionClass(v?: string | null): string {
  const x = safe(v).toUpperCase();
  if (x.includes("FAST 1") || x.includes("FAST 2")) return "cond-fast";
  if (x.includes("GOOD 3") || x.includes("GOOD 4")) return "cond-good";
  if (x.includes("SOFT 5") || x.includes("SOFT 6") || x.includes("SOFT 7")) return "cond-soft";
  if (x.includes("HEAVY 8") || x.includes("HEAVY 9") || x.includes("HEAVY 10")) return "cond-heavy";
  return "cond-unknown";
}

function silkFor(row?: Pick<RatingDisplayRow, "horse" | "silkUrl"> | null): string {
  if (!row) return DEFAULT_SILK_URL;
  return row.silkUrl || getSilksUrl(row.horse);
}

function signalTone(signal: string): SignalState["tone"] {
  const s = signal.toUpperCase();
  if (s === "STEAMER" || s === "FIRMING") return "firming";
  if (s === "DRIFTER" || s === "BIG DRIFTER") return "drifting";
  if (s === "STABLE") return "stable";
  return "none";
}

function signalDisplay(row: MarketSignalRow): SignalState {
  const signal = String(row.market_signal || "NO MARKET").toUpperCase();
  const open = n(row.opening_price);
  const prev = n(row.previous_price);
  const current = n(row.current_price);
  const openPct = n(row.move_from_open_pct);
  const tickPct = n(row.price_delta_pct);
  const from = open && current && open !== current ? open : prev;
  const pctMove = openPct !== null && Math.abs(openPct) > 0.05 ? openPct : tickPct;
  return {
    display: from && current ? `${from.toFixed(2)} -> ${current.toFixed(2)}` : "-",
    change: pctMove !== null ? `${signal} ${pctMove >= 0 ? "+" : ""}${pctMove.toFixed(1)}%` : signal,
    signal,
    tone: signalTone(signal),
  };
}

export default function Worksheet({ runners, selectedHorseKey, onSelectHorse, selectedHorseHistory = [] }: Props): React.ReactElement {
  const [showScratched, setShowScratched] = useState(false);
  const scratchCount = runners.filter((r) => r.isScratched).length;
  const selected = runners.find((r) => r.horseKey === selectedHorseKey && (!r.isScratched || showScratched)) ?? null;

  const sorted = useMemo(() => {
    const seen = new Set<string>();
    return runners
      .filter((r) => showScratched || !r.isScratched)
      .filter((r) => {
        const key = `${r.raceDate}|${r.track}|${r.raceNo}|${r.horseNo}|${r.horseKey}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .sort((a, b) => {
        if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
        return (a.horseNo ?? 999) - (b.horseNo ?? 999);
      });
  }, [runners, showScratched]);

  const lastFive = useMemo(() => selectedHorseHistory.slice(0, 5), [selectedHorseHistory]);
  const [signals, setSignals] = useState<Record<string, SignalState>>({});

  useEffect(() => {
    let active = true;

    function loadSignals() {
      fetch(`/data/market_signals.csv?t=${Date.now()}`, { cache: "no-store" })
        .then((r) => r.text())
        .then((text) => {
          if (!active) return;
          const parsed = Papa.parse<MarketSignalRow>(text, { header: true, skipEmptyLines: true });
          const map: Record<string, SignalState> = {};
          parsed.data.forEach((row) => {
            const key = signalKey(row.track || "", row.race_no || "", row.horse || "", row.horse_key || "");
            if (!key.includes("||")) map[key] = signalDisplay(row);
          });
          setSignals(map);
        })
        .catch(() => {
          if (active) setSignals({});
        });
    }

    loadSignals();
    const timer = window.setInterval(loadSignals, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <section className="edgeiq-ws terminal-panel-stack">
      <div className="edgeiq-ws-card terminal-card">
        <div className="edgeiq-ws-head terminal-card-head">
          <div className="edgeiq-ws-kicker">EDGEiQ RACING / WORKSHEET</div>
          {scratchCount ? <button type="button" className="edgeiq-scr-toggle" onClick={() => setShowScratched((v) => !v)}>{showScratched ? "Hide SCR" : `Show SCR (${scratchCount})`}</button> : null}
        </div>

        <div className="edgeiq-ws-table-wrap aligned-table-wrap worksheet-grid-wrap">
          <table className="edgeiq-ws-table aligned-runner-table worksheet-terminal-table worksheet-fixed-table">
            <colgroup>
              <col className="ws-col-no" />
              <col className="ws-col-silk" />
              <col className="ws-col-runner" />
              <col className="ws-col-jockey" />
              <col className="ws-col-trainer" />
              <col className="ws-col-bar" />
              <col className="ws-col-rated" />
              <col className="ws-col-market" />
              <col className="ws-col-edge" />
              <col className="ws-col-flucs" />
            </colgroup>
            <thead>
              <tr>
                <th>No</th><th>Silk</th><th>Runner</th><th>Jockey</th><th>Trainer</th><th>Bar</th><th>Rated</th><th>Market</th><th>Edge</th><th>Flucs</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => {
                const active = r.horseKey === selectedHorseKey;
                const f = signals[signalKey(r.track, r.raceNo, r.horse, r.horseKey)];
                const flucClass = `edgeiq-fluc-cell edgeiq-fluc-${f?.tone || "none"}`;
                return (
                  <tr key={r.id} onClick={() => !r.isScratched && onSelectHorse(r.horseKey)} className={`${active ? "selected is-selected" : ""} ${r.isScratched ? "scratched is-scratched" : ""}`}>
                    <td className="num saddle-cell"><span>{r.horseNo ?? "-"}</span></td>
                    <td className="silk-cell"><img src={silkFor(r)} alt="" onError={silkFallback} /></td>
                    <td className="runner-text-cell worksheet-runner-name-only"><strong>{r.horse}</strong></td>
                    <td>{safe(r.jockey)}</td>
                    <td>{safe(r.trainer)}</td>
                    <td className="num">{r.barrier ?? "-"}</td>
                    <td className="num">{r.isScratched ? <span className="edgeiq-scr-badge">SCR</span> : price(r.ratedPrice)}</td>
                    <td className="num">{r.isScratched ? <span className="edgeiq-muted">-</span> : marketText(r)}</td>
                    <td className={`num strong ${r.isScratched ? "edgeiq-muted" : edgeTone(r.edgePct)}`}>{r.isScratched ? "-" : pct(r.edgePct)}</td>
                    <td className="flucs-cell">
                      {r.isScratched ? <span className="edgeiq-scr-badge">SCR</span> : f ? <div className={flucClass}><div>{f.display}</div><div className="edgeiq-fluc-change">{f.change}</div></div> : <span className="edgeiq-muted">-</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="edgeiq-ws-card terminal-card edgeiq-snapshot-card">
          <div className="edgeiq-snap-head">
            <div className="edgeiq-runner aligned-runner snapshot-runner">
              <img src={silkFor(selected)} alt="" onError={silkFallback} />
              <div className="edgeiq-runner-meta"><strong>{selected.horse}</strong><span>No {selected.horseNo ?? "-"} | Bar {selected.barrier ?? "-"} | {safe(selected.raceClass)}</span></div>
            </div>
            <div className="edgeiq-snap-metrics">
              <div><span>Rated</span><strong>{price(selected.ratedPrice)}</strong></div>
              <div><span>Market</span><strong>{marketText(selected)}</strong></div>
              <div><span>Edge</span><strong className={edgeTone(selected.edgePct)}>{pct(selected.edgePct)}</strong></div>
            </div>
          </div>

          <div className="edgeiq-form-title">Last 5 official starts</div>
          <div className="edgeiq-ws-table-wrap aligned-table-wrap">
            <table className="edgeiq-ws-table edgeiq-form-table compact-form-table">
              <thead><tr><th>Date</th><th>Track</th><th>Dist</th><th>Class</th><th>Cond</th><th>Fin</th><th>Margin</th><th>Jockey</th><th>SP</th><th>Rating</th><th>Type</th></tr></thead>
              <tbody>
                {lastFive.map((run, i) => <tr key={`${run.id ?? selected.horseKey}-${i}`}><td>{dateShort(run.runDate)}</td><td>{safe(run.track)}</td><td>{safe(run.distance)}</td><td>{safe(run.raceClass)}</td><td><span className={`condition-pill ${conditionClass(run.trackCondition)}`}>{safe(run.trackCondition).toUpperCase()}</span></td><td>{safe(run.finishPos)}</td><td>{safe(run.margin)}</td><td>{safe(run.jockey)}</td><td>{safe(run.sp)}</td><td>{run.runType === "RACE" ? rating(run.runRating) : "-"}</td><td><span className={`edgeiq-pill ${run.runType === "RACE" ? "race" : "trial"}`}>{safe(run.runType)}</span></td></tr>)}
                {lastFive.length === 0 && <tr><td colSpan={11} className="empty">No official form history</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}



