import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { loadRunnerDetail } from "../services/runnerDetailFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";

type EpiRatingsWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

type RunnerRow = { runner: ThreeDayRunner; epi: number | null; epiText: string };

function display(value: unknown, fallback = "-"): string { return cleanProductText(value, fallback); }
function officialNumber(runner: ThreeDayRunner): string { return display(runner.official.no ?? runner.official.number); }
function runnerName(runner: ThreeDayRunner): string { return display(runner.official.runner, "Unnamed runner"); }
function raceTitle(race: ThreeDayRace): string { return display(race.raceName, `Race ${race.raceNumber}`); }
function detailPath(runner: ThreeDayRunner): string { const value = runner.source?.runnerDetailPath; return typeof value === "string" ? value : ""; }

function sourceRecords(runner: ThreeDayRunner): Record<string, unknown>[] {
  const records: Record<string, unknown>[] = [];
  if (runner.source && typeof runner.source === "object") records.push(runner.source);
  const official = runner.official as unknown as Record<string, unknown>;
  if (official && typeof official === "object") records.push(official);
  return records;
}

const EPI_KEYS = ["epi", "EPI", "epi_rating", "epiRating", "edgeiq_epi", "edgeiqEpi", "edgeiq_epi_rating", "edgeiqEpiRating"];

function epiValue(runner: ThreeDayRunner): { value: number | null; text: string } {
  for (const record of sourceRecords(runner)) {
    for (const key of EPI_KEYS) {
      const raw = record[key];
      if (raw === null || raw === undefined || String(raw).trim() === "") continue;
      const numeric = Number(raw);
      if (Number.isFinite(numeric)) return { value: numeric, text: numeric.toFixed(2) };
      return { value: null, text: String(raw).trim() };
    }
  }
  return { value: null, text: "-" };
}

export function EpiRatingsWorkspace({ meeting, selectedRaceKey, onRaceChange }: EpiRatingsWorkspaceProps) {
  const selectedRace = useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);

  const [rows, setRows] = useState<RunnerRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    if (!selectedRace) {
      setRows([]);
      return () => { active = false; };
    }
    setLoading(true);
    Promise.all(selectedRace.runners.map(async (runner) => {
      const path = detailPath(runner);
      let fullRunner = runner;
      if (path) {
        try { fullRunner = await loadRunnerDetail(path); } catch { fullRunner = runner; }
      }
      const epi = epiValue(fullRunner);
      return { runner: fullRunner, epi: epi.value, epiText: epi.text } satisfies RunnerRow;
    })).then((next) => {
      if (!active) return;
      next.sort((a, b) => {
        if (a.epi === null && b.epi === null) return Number(officialNumber(a.runner)) - Number(officialNumber(b.runner));
        if (a.epi === null) return 1;
        if (b.epi === null) return -1;
        return b.epi - a.epi;
      });
      setRows(next);
      setLoading(false);
    });
    return () => { active = false; };
  }, [selectedRace]);

  if (!meeting || !selectedRace) return null;

  return (
    <section className="eiq-epi-v1" aria-label="EPI Ratings workspace" data-edgeiq-workspace-key="EPI_RATINGS">
      <header className="eiq-epi-v1__header">
        <div><p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p><h1>EPI Ratings</h1></div>
        <strong>{selectedRace.runners.length} runners</strong>
      </header>

      <nav className="eiq-epi-v1__race-tabs" aria-label="Meeting races">
        {meeting.races.map((race) => <button key={race.raceKey} type="button" className={race.raceKey === selectedRace.raceKey ? "is-active" : ""} onClick={() => onRaceChange(race.raceKey)}><strong>R{race.raceNumber}</strong><span>{display(race.raceTime)}</span></button>)}
      </nav>

      <section className="eiq-epi-v1__card">
        <header><div><h2>{raceTitle(selectedRace)}</h2><p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p></div><strong>{loading ? "Loading…" : `${rows.filter((row) => row.epiText !== "-").length} rated`}</strong></header>
        <div className="eiq-epi-v1__table-wrap">
          <table>
            <thead><tr><th>Rank</th><th>No.</th><th>Runner</th><th>Barrier</th><th>Jockey</th><th>Trainer</th><th>Weight</th><th>EPI</th></tr></thead>
            <tbody>
              {(rows.length ? rows : selectedRace.runners.map((runner) => ({ runner, epi: null, epiText: "-" }))).map((row, index) => <tr key={`${officialNumber(row.runner)}-${runnerName(row.runner)}-${index}`}><td><span className="eiq-epi-v1__rank">{row.epiText === "-" ? "-" : index + 1}</span></td><td>{officialNumber(row.runner)}</td><td><strong>{runnerName(row.runner)}</strong></td><td>{display(row.runner.official.barrier)}</td><td>{display(row.runner.official.jockey)}</td><td>{display(row.runner.official.trainer)}</td><td>{display(row.runner.official.weight)}</td><td><b className="eiq-epi-v1__rating">{row.epiText}</b></td></tr>)}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
