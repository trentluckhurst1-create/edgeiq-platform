import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import { EDGEIQ_LIVE_FILES, EDGEIQ_REFRESH_MS } from "../config/edgeiqLiveFeeds";
import { isVicTrack } from "../config/edgeiqVicTracks";

type Row = Record<string, string | number | undefined>;
type StatusRow = Record<string, string>;
type Tone = "good" | "warn" | "bad" | "neutral";

function clean(value: unknown): string {
  const output = String(value ?? "").trim();
  return output && output !== "-" && output.toUpperCase() !== "NAN" ? output : "";
}

function num(value: unknown): number | null {
  const cleaned = clean(value).replace(/[^\d.-]/g, "");
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function price(value: unknown): string {
  const parsed = num(value);
  return parsed === null || parsed <= 0 ? "-" : `$${parsed.toFixed(2)}`;
}

function pct(value: unknown): string {
  const parsed = num(value);
  return parsed === null ? "-" : `${parsed.toFixed(1)}%`;
}

function first(row: Row, keys: string[]): string {
  for (const key of keys) {
    const value = clean(row[key]);
    if (value) return value;
  }
  return "";
}

function firstNum(row: Row, keys: string[]): number | null {
  for (const key of keys) {
    const value = num(row[key]);
    if (value !== null) return value;
  }
  return null;
}

async function loadCsv(path: string): Promise<Row[]> {
  const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} HTTP ${response.status}`);
  const csv = await response.text();
  const parsed = Papa.parse<Row>(csv, { header: true, skipEmptyLines: true });
  return (parsed.data || []).filter(Boolean);
}

async function loadOptionalCsv(path: string): Promise<Row[]> {
  try {
    return await loadCsv(path);
  } catch {
    return [];
  }
}

function toneClass(tone: Tone): string {
  if (tone === "good") return "positive";
  if (tone === "warn") return "warning";
  if (tone === "bad") return "negative";
  return "neutral";
}

function statusTone(status: string): Tone {
  const value = clean(status).toUpperCase();
  if (value.includes("FRESH") || value.includes("READY")) return "good";
  if (value.includes("BLOCKED") || value.includes("FAILED")) return "bad";
  if (value.includes("STALE") || value.includes("EMPTY") || value.includes("SCHEMA")) return "warn";
  return "neutral";
}

export default function LiveMarketMovers(): React.ReactElement {
  const [terminalRows, setTerminalRows] = useState<Row[]>([]);
  const [marketRows, setMarketRows] = useState<Row[]>([]);
  const [statusRows, setStatusRows] = useState<StatusRow[]>([]);
  const [updatedAt, setUpdatedAt] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load(): Promise<void> {
      try {
        const [terminal, market, status] = await Promise.all([
          loadOptionalCsv(EDGEIQ_LIVE_FILES.terminalFeed),
          loadOptionalCsv("/data/sportsbet_live_market_v1.csv"),
          loadOptionalCsv("/data/sportsbet_live_market_status_v1.csv"),
        ]);

        if (!active) return;

        setTerminalRows(terminal.filter((row) => isVicTrack(first(row, ["track", "track_name", "meeting"]))));
        setMarketRows(market.filter((row) => isVicTrack(first(row, ["track", "track_name", "meeting_name"]))));        
        setStatusRows(status as StatusRow[]);
        setUpdatedAt(new Date().toLocaleTimeString());
        setError("");
      } catch (loadError) {
        if (!active) return;
        setTerminalRows([]);
        setMarketRows([]);
        setStatusRows([]);
        setUpdatedAt(new Date().toLocaleTimeString());
        setError(String(loadError));
      }
    }

    load();
    const interval = window.setInterval(load, EDGEIQ_REFRESH_MS || 15000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const statusSummary = useMemo(() => {
    const row = statusRows[0] ?? {};
    const fallbackTracks = new Set(marketRows.map((marketRow) => first(marketRow, ["track", "meeting_name"])).filter(Boolean)).size;
    const fallbackRaces = new Set(marketRows.map((marketRow) => `${first(marketRow, ["track", "meeting_name"])}|${first(marketRow, ["race_no", "race_number"])}`).filter(Boolean)).size;
    const sourceStatus = clean(row.source_status) || clean(marketRows[0]?.source_status) || "UNAVAILABLE";
    const tracks = clean(row.tracks_captured) || (fallbackTracks ? String(fallbackTracks) : "0");
    const races = clean(row.races_captured) || (fallbackRaces ? String(fallbackRaces) : "0");
    const prices = clean(row.prices_captured) || (marketRows.length ? String(marketRows.length) : "0");
    const note = clean(row.notes) || (marketRows.length ? `captured ${marketRows.length} current prices from owned Sportsbet market rows` : "No Sportsbet capture summary available.");
    const capturedAt = clean(row.capture_timestamp_utc) || "";

    return {
      sourceStatus,
      tracks,
      races,
      prices,
      note,
      capturedAt,
    };
  }, [marketRows, statusRows]);

  const pricedRows = useMemo(() => {
    return terminalRows
      .map((row) => {
        const current = firstNum(row, ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win"]);
        const previous = firstNum(row, ["open_price", "mid_price", "close_price"]);
        const edge = firstNum(row, ["ui_edge_pct", "edge_pct"]);
        const movePct =
          previous !== null && current !== null && previous > 0
            ? ((current - previous) / previous) * 100
            : null;

        return {
          track: first(row, ["track", "meeting"]),
          raceNo: first(row, ["race_no", "race_number"]),
          horse: first(row, ["horse"]),
          action: first(row, ["execution_action", "truth_grade", "suppression_action"]) || "OBSERVE",
          current,
          previous,
          movePct,
          edge,
          liveRank: firstNum(row, ["live_rank"]),
          sourceStatus: first(row, ["market_source_status", "ui_status"]),
          sourceReady: first(row, ["market_source_ready"]),
        };
      })
      .filter((row) => row.horse && row.current !== null)
      .sort((a, b) => {
        const moveA = Math.abs(a.movePct ?? 0);
        const moveB = Math.abs(b.movePct ?? 0);
        if (moveA !== moveB) return moveB - moveA;
        if ((a.liveRank ?? 999) !== (b.liveRank ?? 999)) return (a.liveRank ?? 999) - (b.liveRank ?? 999);
        return (a.current ?? 999) - (b.current ?? 999);
      });
  }, [terminalRows]);

  const movers = useMemo(() => pricedRows.filter((row) => Math.abs(row.movePct ?? 0) >= 0.5).slice(0, 8), [pricedRows]);
  const pricedBoard = useMemo(() => pricedRows.slice(0, 8), [pricedRows]);

  const counts = useMemo(() => {
    const priced = pricedRows.length;
    const tracks = new Set(pricedRows.map((row) => row.track)).size;
    const races = new Set(pricedRows.map((row) => `${row.track}|${row.raceNo}`)).size;
    return {
      terminal: terminalRows.length,
      sportsbetRows: marketRows.length,
      tracks,
      races,
      priced,
    };
  }, [marketRows.length, pricedRows, terminalRows.length]);

  return (
    <section className="terminal-card overflow-hidden">
      <div className="terminal-card-head">
        <div>
          <div className="terminal-kicker">
            VIC MARKET WATCH
          </div>
          <div className="mt-1 text-[18px] font-black text-white">
            Victoria Price Monitor
          </div>
        </div>

        <div className="text-right">
          <div className="terminal-meta terminal-faint">
            UI poll
          </div>
          <div className="terminal-positive text-sm font-black">
            {updatedAt || "-"}
          </div>
        </div>
      </div>

      <div className="terminal-band">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className={`terminal-chip ${toneClass(statusTone(statusSummary.sourceStatus))}`}>
            Sportsbet {statusSummary.sourceStatus}
          </span>
          <span className="terminal-chip neutral">
            {statusSummary.prices} prices
          </span>
          <span className="terminal-chip neutral">
            {statusSummary.tracks} tracks
          </span>
          <span className="terminal-chip neutral">
            {statusSummary.races} races
          </span>
        </div>

        <div className="terminal-text text-[11px] leading-5">
          {statusSummary.note}
          {statusSummary.capturedAt ? <span className="terminal-faint"> | capture {statusSummary.capturedAt}</span> : null}
        </div>
      </div>

      <div className="terminal-grid five">
        <Mini label="Terminal rows" value={counts.terminal} />
        <Mini label="Sportsbet rows" value={counts.sportsbetRows} />
        <Mini label="Tracks" value={counts.tracks} />
        <Mini label="Races" value={counts.races} />
        <Mini label="Priced runners" value={counts.priced} />
      </div>

      {error ? (
        <div className="terminal-error">
          {error}
        </div>
      ) : null}

      <div className="grid gap-0 md:grid-cols-2">
        <div className="border-b border-white/5 md:border-b-0 md:border-r md:border-r-white/5">
          <div className="terminal-section-title">
            {movers.length ? "Price movers" : "Current price board"}
          </div>

          <div className="divide-y divide-white/5">
            {(movers.length ? movers : pricedBoard).map((row, index) => {
              const moveTone: Tone =
                (row.movePct ?? 0) < -0.01 ? "good" :
                (row.movePct ?? 0) > 0.01 ? "warn" :
                "neutral";

              return (
                <div key={`${row.track}-${row.raceNo}-${row.horse}-${index}`} className="terminal-list-row">
                  <div className="min-w-0">
                    <div className="truncate text-[13px] font-black text-white">{row.horse}</div>
                    <div className="terminal-meta terminal-faint mt-1">
                      {row.track} R{row.raceNo} | {row.action || "OBSERVE"}
                    </div>
                  </div>

                  <div className="ml-4 flex items-center gap-3 text-right">
                    <div>
                      <div className="terminal-meta terminal-faint">Price</div>
                      <div className="text-[13px] font-black text-white">{price(row.current)}</div>
                    </div>
                    <div>
                      <div className="terminal-meta terminal-faint">Edge</div>
                      <div className={`text-[13px] font-black ${(row.edge ?? 0) > 0 ? "terminal-positive" : "terminal-muted"}`}>
                        {pct(row.edge)}
                      </div>
                    </div>
                    <span className={`terminal-chip ${toneClass(moveTone)}`}>
                      {row.movePct === null ? (row.sourceReady || row.sourceStatus || "PRICED") : pct(row.movePct)}
                    </span>
                  </div>
                </div>
              );
            })}

            {!movers.length && !pricedBoard.length ? (
              <div className="terminal-empty">
                No priced VIC runners are available in the owned terminal feed.
              </div>
            ) : null}
          </div>
        </div>

        <div>
          <div className="terminal-section-title">
            Feed context
          </div>
          <div className="terminal-grid">
            <ContextRow label="Capture source" value={`Sportsbet ${statusSummary.sourceStatus}`} tone={statusTone(statusSummary.sourceStatus)} />
            <ContextRow label="Terminal coverage" value={`${counts.priced} priced runners across ${counts.races} races`} />
            <ContextRow label="Market breadth" value={`${statusSummary.prices} price points from ${statusSummary.tracks} VIC track group(s)`} />
            <ContextRow
              label="Empty-state truth"
              value={movers.length ? "Mover deltas are available." : "No mover deltas yet. Board is showing current prices instead of fake momentum."}
              tone={movers.length ? "good" : "warn"}
            />
            <ContextRow label="Observed note" value={statusSummary.note} />
          </div>
        </div>
      </div>
    </section>
  );
}

function Mini({ label, value }: { label: string; value: string | number }): React.ReactElement {
  return (
    <div className="terminal-metric neutral">
      <span>{label}</span>
      <div className="text-[16px] font-black text-white">{value}</div>
    </div>
  );
}

function ContextRow({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: Tone;
}): React.ReactElement {
  return (
    <div className={`terminal-metric ${tone}`}>
      <span>{label}</span>
      <div className="mt-1 text-[12px] font-bold">
        {value}
      </div>
    </div>
  );
}


