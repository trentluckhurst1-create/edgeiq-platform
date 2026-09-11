import { useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { loadRunnerDetail } from "../services/runnerDetailFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";

type FormWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

type RunnerState = { runner: ThreeDayRunner; loading: boolean; error: string };

function display(value: unknown, fallback = "-"): string {
  return cleanProductText(value, fallback);
}

function officialNumber(runner: ThreeDayRunner): string {
  return display(runner.official.no ?? runner.official.number);
}

function runnerName(runner: ThreeDayRunner): string {
  return display(runner.official.runner, "Unnamed runner");
}

function raceTitle(race: ThreeDayRace): string {
  return display(race.raceName, `Race ${race.raceNumber}`);
}

function detailPath(runner: ThreeDayRunner): string {
  const value = runner.source?.runnerDetailPath;
  return typeof value === "string" ? value : "";
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function first(record: Record<string, unknown>, keys: string[], fallback = "-"): string {
  for (const key of keys) {
    const value = String(record[key] ?? "").trim();
    if (value && value !== "-") return value;
  }
  return fallback;
}

function formString(runner: ThreeDayRunner): string {
  const value = runner.source?.last_five ?? runner.source?.form;
  if (Array.isArray(value)) return value.map((item) => String(item ?? "").trim()).filter(Boolean).join("-") || "-";
  return display(value);
}

function recentRuns(runner: ThreeDayRunner): unknown[] {
  const runs = Array.isArray(runner.historicalRuns) && runner.historicalRuns.length
    ? runner.historicalRuns
    : Array.isArray(runner.evidenceRuns) ? runner.evidenceRuns : [];
  return runs.slice(0, 5);
}

export function FormWorkspace({ meeting, selectedRaceKey, onRaceChange }: FormWorkspaceProps) {
  const [expandedKey, setExpandedKey] = useState("");
  const [loaded, setLoaded] = useState<Record<string, RunnerState>>({});

  const selectedRace = useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);

  if (!meeting || !selectedRace) return null;

  async function toggleRunner(runner: ThreeDayRunner, index: number) {
    const key = `${selectedRace.raceKey}:${officialNumber(runner)}:${index}`;
    if (expandedKey === key) {
      setExpandedKey("");
      return;
    }
    setExpandedKey(key);
    if (loaded[key]?.runner && !loaded[key].loading) return;

    const path = detailPath(runner);
    if (!path) {
      setLoaded((current) => ({ ...current, [key]: { runner, loading: false, error: "Form detail not supplied." } }));
      return;
    }

    setLoaded((current) => ({ ...current, [key]: { runner, loading: true, error: "" } }));
    try {
      const fullRunner = await loadRunnerDetail(path);
      setLoaded((current) => ({ ...current, [key]: { runner: fullRunner, loading: false, error: "" } }));
    } catch (error) {
      setLoaded((current) => ({ ...current, [key]: { runner, loading: false, error: error instanceof Error ? error.message : "Form detail unavailable" } }));
    }
  }

  return (
    <section className="eiq-form-v1" aria-label="Form workspace" data-edgeiq-workspace-key="FORM">
      <header className="eiq-form-v1__header">
        <div>
          <p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p>
          <h1>Form</h1>
        </div>
        <strong>{selectedRace.runners.length} runners</strong>
      </header>

      <nav className="eiq-form-v1__race-tabs" aria-label="Meeting races">
        {meeting.races.map((race) => (
          <button key={race.raceKey} type="button" className={race.raceKey === selectedRace.raceKey ? "is-active" : ""} onClick={() => onRaceChange(race.raceKey)}>
            <strong>R{race.raceNumber}</strong>
            <span>{display(race.raceTime)}</span>
          </button>
        ))}
      </nav>

      <section className="eiq-form-v1__card">
        <header>
          <div><h2>{raceTitle(selectedRace)}</h2><p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p></div>
          <strong>{selectedRace.runners.length} declared</strong>
        </header>

        <div className="eiq-form-v1__table-wrap">
          <table>
            <thead>
              <tr><th>No.</th><th>Runner</th><th>Last 5</th><th>Barrier</th><th>Jockey</th><th>Weight</th><th /></tr>
            </thead>
            <tbody>
              {selectedRace.runners.map((runner, index) => {
                const key = `${selectedRace.raceKey}:${officialNumber(runner)}:${index}`;
                const isExpanded = expandedKey === key;
                const state = loaded[key];
                const fullRunner = state?.runner ?? runner;
                const runs = recentRuns(fullRunner);
                return [
                  <tr key={`${key}:main`} className={isExpanded ? "is-expanded" : ""}>
                    <td><span className="eiq-form-v1__number">{officialNumber(runner)}</span></td>
                    <td><strong>{runnerName(runner)}</strong><small>{display(runner.official.trainer)}</small></td>
                    <td><b className="eiq-form-v1__figures">{formString(runner)}</b></td>
                    <td>{display(runner.official.barrier)}</td>
                    <td>{display(runner.official.jockey)}</td>
                    <td>{display(runner.official.weight)}</td>
                    <td><button type="button" onClick={() => void toggleRunner(runner, index)}>{isExpanded ? "−" : "+"}</button></td>
                  </tr>,
                  isExpanded ? (
                    <tr key={`${key}:detail`} className="eiq-form-v1__detail-row">
                      <td colSpan={7}>
                        {state?.loading ? <p className="eiq-form-v1__message">Loading…</p> : null}
                        {!state?.loading && state?.error ? <p className="eiq-form-v1__message">{state.error}</p> : null}
                        {!state?.loading && !state?.error && runs.length ? (
                          <div className="eiq-form-v1__runs">
                            <div className="eiq-form-v1__runs-head"><span>Date</span><span>Track</span><span>Dist.</span><span>Going</span><span>Class</span><span>Finish</span><span>Margin</span><span>Rating</span></div>
                            {runs.map((run, runIndex) => {
                              const record = asRecord(run);
                              return <div className="eiq-form-v1__run" key={runIndex}>
                                <span>{first(record,["date","race_date","meeting_date","raceDate"])}</span>
                                <span>{first(record,["track","meeting","venue","track_name","meetingName"])}</span>
                                <span>{first(record,["distance","dist","race_distance"])}</span>
                                <span>{first(record,["going","track_condition","trackCondition","condition"])}</span>
                                <span>{first(record,["class","race_class","raceClass"])}</span>
                                <span>{first(record,["finish","position","placing","place"])}</span>
                                <span>{first(record,["margin","margin_beaten","beaten_margin","beatenMargin"])}</span>
                                <span>{first(record,["rating","wfa","form_rating","performance_rating","figure"])}</span>
                              </div>;
                            })}
                          </div>
                        ) : null}
                        {!state?.loading && !state?.error && !runs.length ? <p className="eiq-form-v1__message">No recent runs supplied.</p> : null}
                      </td>
                    </tr>
                  ) : null,
                ];
              })}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
