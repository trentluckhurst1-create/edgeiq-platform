import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import {
  canonicalRailDisplay,
  canonicalTrackDisplayName,
  canonicalTrackRatingDisplay,
  cleanProductText,
} from "../../design-system/presentation";

type RaceWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
  onBackToMeetings: () => void;
};

function display(value: unknown, fallback = "Not supplied"): string {
  return cleanProductText(value, fallback);
}

function officialNumber(runner: ThreeDayRunner): string {
  return display(runner.official.no ?? runner.official.number, "-");
}

function runnerName(runner: ThreeDayRunner): string {
  return display(runner.official.runner, "Unnamed runner");
}

function marketText(runner: ThreeDayRunner): string {
  const value = runner.official.market;
  if (typeof value === "number" && Number.isFinite(value)) return `$${value.toFixed(2)}`;
  const text = String(value ?? "").trim();
  if (!text) return "-";
  if (/^\d+(\.\d+)?$/.test(text)) return `$${Number(text).toFixed(2)}`;
  return text;
}

function raceTitle(race: ThreeDayRace): string {
  const name = display(race.raceName, "");
  return name && name !== "Not supplied" ? name : `Race ${race.raceNumber}`;
}

export function RaceWorkspace({
  meeting,
  selectedRaceKey,
  onRaceChange,
  onBackToMeetings,
}: RaceWorkspaceProps) {
  if (!meeting || !meeting.races.length) return null;

  const selectedRace = meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  const runners = selectedRace.runners ?? [];

  return (
    <section className="eiq-race-v1" aria-label="Race workspace" data-edgeiq-workspace-key="RACE">
      <header className="eiq-race-v1__header">
        <div>
          <button type="button" className="eiq-race-v1__back" onClick={onBackToMeetings}>← Meetings</button>
          <p className="eiq-race-v1__eyebrow">{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p>
          <div className="eiq-race-v1__title-row">
            <span className="eiq-race-v1__race-number">R{selectedRace.raceNumber}</span>
            <div>
              <h1>{raceTitle(selectedRace)}</h1>
              <p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p>
            </div>
          </div>
        </div>
        <div className="eiq-race-v1__status">
          <span>Race time</span>
          <strong>{display(selectedRace.raceTime)}</strong>
        </div>
      </header>

      <nav className="eiq-race-v1__race-tabs" aria-label="Meeting races">
        {meeting.races.map((race) => (
          <button
            key={race.raceKey}
            type="button"
            className={race.raceKey === selectedRace.raceKey ? "is-active" : ""}
            onClick={() => onRaceChange(race.raceKey)}
          >
            <strong>R{race.raceNumber}</strong>
            <span>{display(race.raceTime, "-")}</span>
          </button>
        ))}
      </nav>

      <div className="eiq-race-v1__facts" aria-label="Race details">
        <article><span>Distance</span><strong>{display(selectedRace.distance)}</strong></article>
        <article><span>Class</span><strong>{display(selectedRace.raceClass)}</strong></article>
        <article><span>Track</span><strong>{canonicalTrackRatingDisplay(selectedRace.trackCondition ?? meeting.trackCondition)}</strong></article>
        <article><span>Rail</span><strong>{canonicalRailDisplay(selectedRace.rail ?? meeting.rail)}</strong></article>
        <article><span>Field</span><strong>{runners.length || display(selectedRace.source?.field_size)}</strong></article>
      </div>

      <section className="eiq-race-v1__board">
        <header>
          <div>
            <h2>Runner Board</h2>
            <p>Declared runners and currently supplied race information.</p>
          </div>
          <strong>{runners.length} runners</strong>
        </header>

        <div className="eiq-race-v1__table-wrap">
          <table>
            <thead>
              <tr>
                <th>No.</th>
                <th>Runner</th>
                <th>Barrier</th>
                <th>Jockey</th>
                <th>Trainer</th>
                <th>Weight</th>
                <th>Market</th>
              </tr>
            </thead>
            <tbody>
              {runners.map((runner, index) => (
                <tr key={`${officialNumber(runner)}-${runnerName(runner)}-${index}`}>
                  <td><span className="eiq-race-v1__runner-no">{officialNumber(runner)}</span></td>
                  <td><strong>{runnerName(runner)}</strong></td>
                  <td>{display(runner.official.barrier, "-")}</td>
                  <td>{display(runner.official.jockey, "-")}</td>
                  <td>{display(runner.official.trainer, "-")}</td>
                  <td>{display(runner.official.weight, "-")}</td>
                  <td><strong>{marketText(runner)}</strong></td>
                </tr>
              ))}
              {!runners.length ? (
                <tr><td colSpan={7} className="eiq-race-v1__empty">Runner detail has not been loaded for this race.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
