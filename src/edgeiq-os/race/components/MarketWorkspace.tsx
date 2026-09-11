import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { loadRunnerDetail } from "../services/runnerDetailFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";

type MarketWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

type MarketRow = { runner: ThreeDayRunner; market: string; fair: string; edge: string };

function display(value: unknown, fallback = "-"): string { return cleanProductText(value, fallback); }
function officialNumber(runner: ThreeDayRunner): string { return display(runner.official.no ?? runner.official.number); }
function runnerName(runner: ThreeDayRunner): string { return display(runner.official.runner, "Unnamed runner"); }
function raceTitle(race: ThreeDayRace): string { return display(race.raceName, `Race ${race.raceNumber}`); }
function detailPath(runner: ThreeDayRunner): string { const value = runner.source?.runnerDetailPath; return typeof value === "string" ? value : ""; }
function price(value: unknown): string { const text = String(value ?? "").trim(); if (!text) return "-"; const numeric = Number(text.replace(/^\$/,"")); return Number.isFinite(numeric) ? `$${numeric.toFixed(2)}` : text; }
function first(record: Record<string, unknown>, keys: string[]): unknown { for (const key of keys) { const value = record[key]; if (value !== null && value !== undefined && String(value).trim() !== "") return value; } return null; }

const FAIR_KEYS = ["fair", "fair_price", "fairPrice", "edgeiq_price", "edgeiqPrice", "model_price", "modelPrice"];
const EDGE_KEYS = ["edge", "edge_pct", "edgePct", "edge_percent", "edgePercent", "market_edge", "marketEdge"];

function marketRow(runner: ThreeDayRunner): MarketRow {
  const source = runner.source ?? {};
  const marketValue = runner.official.market ?? first(source, ["market", "price", "current_price", "currentPrice"]);
  const fairValue = first(source, FAIR_KEYS);
  const edgeValue = first(source, EDGE_KEYS);
  return { runner, market: price(marketValue), fair: price(fairValue), edge: edgeValue === null ? "-" : display(edgeValue) };
}

export function MarketWorkspace({ meeting, selectedRaceKey, onRaceChange }: MarketWorkspaceProps) {
  const selectedRace = useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);

  const [rows, setRows] = useState<MarketRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    if (!selectedRace) { setRows([]); return () => { active = false; }; }
    setLoading(true);
    Promise.all(selectedRace.runners.map(async (runner) => {
      const path = detailPath(runner);
      let fullRunner = runner;
      if (path) {
        try { fullRunner = await loadRunnerDetail(path); } catch { fullRunner = runner; }
      }
      return marketRow(fullRunner);
    })).then((next) => {
      if (!active) return;
      next.sort((a,b) => {
        const pa = Number(a.market.replace("$",""));
        const pb = Number(b.market.replace("$",""));
        if (Number.isFinite(pa) && Number.isFinite(pb)) return pa - pb;
        if (Number.isFinite(pa)) return -1;
        if (Number.isFinite(pb)) return 1;
        return Number(officialNumber(a.runner)) - Number(officialNumber(b.runner));
      });
      setRows(next);
      setLoading(false);
    });
    return () => { active = false; };
  }, [selectedRace]);

  if (!meeting || !selectedRace) return null;
  const shownRows = rows.length ? rows : selectedRace.runners.map(marketRow);

  return (
    <section className="eiq-market-clean-v1" aria-label="Market workspace" data-edgeiq-workspace-key="MARKET">
      <header className="eiq-market-clean-v1__header"><div><p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p><h1>Market</h1></div><strong>{selectedRace.runners.length} runners</strong></header>
      <nav className="eiq-market-clean-v1__race-tabs" aria-label="Meeting races">{meeting.races.map((race) => <button key={race.raceKey} type="button" className={race.raceKey === selectedRace.raceKey ? "is-active" : ""} onClick={() => onRaceChange(race.raceKey)}><strong>R{race.raceNumber}</strong><span>{display(race.raceTime)}</span></button>)}</nav>
      <section className="eiq-market-clean-v1__card">
        <header><div><h2>{raceTitle(selectedRace)}</h2><p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p></div><strong>{loading ? "Loading…" : `${shownRows.filter((row) => row.market !== "-").length} priced`}</strong></header>
        <div className="eiq-market-clean-v1__table-wrap"><table><thead><tr><th>No.</th><th>Runner</th><th>Barrier</th><th>Jockey</th><th>Weight</th><th>Market</th><th>Fair</th><th>Edge</th></tr></thead><tbody>{shownRows.map((row,index) => <tr key={`${officialNumber(row.runner)}-${runnerName(row.runner)}-${index}`}><td>{officialNumber(row.runner)}</td><td><strong>{runnerName(row.runner)}</strong><small>{display(row.runner.official.trainer)}</small></td><td>{display(row.runner.official.barrier)}</td><td>{display(row.runner.official.jockey)}</td><td>{display(row.runner.official.weight)}</td><td><b className="eiq-market-clean-v1__market">{row.market}</b></td><td><b className="eiq-market-clean-v1__fair">{row.fair}</b></td><td><b>{row.edge}</b></td></tr>)}</tbody></table></div>
      </section>
    </section>
  );
}
