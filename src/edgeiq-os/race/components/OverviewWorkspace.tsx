import { useMemo } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { canonicalRailDisplay, canonicalTrackDisplayName, canonicalTrackRatingDisplay, cleanProductText } from "../../design-system/presentation";

type OverviewWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

function display(value: unknown, fallback = "-"): string {
  return cleanProductText(value, fallback);
}

function raceTitle(race: ThreeDayRace): string {
  const value = display(race.raceName, "");
  return value || `Race ${race.raceNumber}`;
}

function runnerName(runner: ThreeDayRunner): string {
  return display(runner.official.runner, "Unnamed runner");
}

function runnerNumber(runner: ThreeDayRunner): string {
  return display(runner.official.no ?? runner.official.number);
}

function hasHistory(runner: ThreeDayRunner): boolean {
  return (Array.isArray(runner.historicalRuns) && runner.historicalRuns.length > 0)
    || (Array.isArray(runner.evidenceRuns) && runner.evidenceRuns.length > 0);
}

function hasMarket(runner: ThreeDayRunner): boolean {
  const value = runner.official.market;
  return value !== null && value !== undefined && String(value).trim() !== "" && String(value).trim() !== "-";
}

function hasDetail(runner: ThreeDayRunner): boolean {
  return typeof runner.source?.runnerDetailPath === "string" && runner.source.runnerDetailPath.length > 0;
}

export function OverviewWorkspace({ meeting, selectedRaceKey, onRaceChange }: OverviewWorkspaceProps) {
  const selectedRace = useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);

  if (!meeting || !selectedRace) return null;

  const runners = selectedRace.runners ?? [];
  const marketCount = runners.filter(hasMarket).length;
  const historyCount = runners.filter(hasHistory).length;
  const detailCount = runners.filter(hasDetail).length;

  return (
    <section className="eiq-overview-v1" aria-label="Overview workspace" data-edgeiq-workspace-key="OVERVIEW">
      <header className="eiq-overview-v1__header">
        <div>
          <p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p>
          <h1>Overview</h1>
        </div>
        <strong>R{selectedRace.raceNumber}</strong>
      </header>

      <nav className="eiq-overview-v1__race-tabs" aria-label="Meeting races">
        {meeting.races.map((race) => (
          <button key={race.raceKey} type="button" className={race.raceKey === selectedRace.raceKey ? "is-active" : ""} onClick={() => onRaceChange(race.raceKey)}>
            <strong>R{race.raceNumber}</strong>
            <span>{display(race.raceTime)}</span>
          </button>
        ))}
      </nav>

      <section className="eiq-overview-v1__race-card">
        <div>
          <span>R{selectedRace.raceNumber}</span>
          <div><h2>{raceTitle(selectedRace)}</h2><p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p></div>
        </div>
        <strong>{display(selectedRace.raceTime, "Not supplied")}</strong>
      </section>

      <div className="eiq-overview-v1__facts">
        <article><span>Track</span><strong>{canonicalTrackRatingDisplay(selectedRace.trackCondition ?? meeting.trackCondition)}</strong></article>
        <article><span>Rail</span><strong>{canonicalRailDisplay(selectedRace.rail ?? meeting.rail)}</strong></article>
        <article><span>Field</span><strong>{runners.length}</strong></article>
        <article><span>Market</span><strong>{marketCount}/{runners.length}</strong></article>
        <article><span>History</span><strong>{historyCount}/{runners.length}</strong></article>
        <article><span>Detail</span><strong>{detailCount}/{runners.length}</strong></article>
      </div>

      <section className="eiq-overview-v1__board">
        <header><h2>Field Snapshot</h2><strong>{runners.length} runners</strong></header>
        <div className="eiq-overview-v1__table-wrap">
          <table>
            <thead><tr><th>No.</th><th>Runner</th><th>Barrier</th><th>Jockey</th><th>Trainer</th><th>Weight</th><th>Market</th></tr></thead>
            <tbody>
              {runners.map((runner, index) => (
                <tr key={`${runnerNumber(runner)}-${runnerName(runner)}-${index}`}>
                  <td><span className="eiq-overview-v1__number">{runnerNumber(runner)}</span></td>
                  <td><strong>{runnerName(runner)}</strong></td>
                  <td>{display(runner.official.barrier)}</td>
                  <td>{display(runner.official.jockey)}</td>
                  <td>{display(runner.official.trainer)}</td>
                  <td>{display(runner.official.weight)}</td>
                  <td>{display(runner.official.market)}</td>
                </tr>
              ))}
              {!runners.length ? <tr><td colSpan={7} className="eiq-overview-v1__empty">No runner data supplied.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
