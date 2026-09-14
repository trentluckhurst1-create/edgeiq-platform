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

function formTokens(runner: ThreeDayRunner): string[] {
  const raw = formString(runner);
  if (!raw || raw === "-") return [];
  return raw.split(/[-,\s]+/).map((item) => item.trim()).filter(Boolean).slice(-5);
}

function recentRuns(runner: ThreeDayRunner): unknown[] {
  const runs = Array.isArray(runner.historicalRuns) && runner.historicalRuns.length
    ? runner.historicalRuns
    : Array.isArray(runner.evidenceRuns) ? runner.evidenceRuns : [];
  return runs.slice(0, 5);
}

function finishTone(value: string): string {
  const n = Number.parseInt(value, 10);
  if (n === 1) return "is-win";
  if (n === 2 || n === 3) return "is-place";
  return "";
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
          <span className="eiq-form-v1__subtitle">Runner form, recent performance and race context</span>
        </div>
        <div className="eiq-form-v1__header-count">
          <span>Field</span>
          <strong>{selectedRace.runners.length}</strong>
          <small>runners</small>
        </div>
      </header>

      <nav className="eiq-form-v1__race-tabs" aria-label="Meeting races">
        {meeting.races.map((race) => (
          <button key={race.raceKey} type="button" className={race.raceKey === selectedRace.raceKey ? "is-active" : ""} onClick={() => onRaceChange(race.raceKey)}>
            <strong>R{race.raceNumber}</strong>
            <span>{display(race.raceTime)}</span>
          </button>
        ))}
      </nav>

      <section className="eiq-form-v1__race-strip">
        <div><span>Race</span><strong>R{selectedRace.raceNumber}</strong></div>
        <div><span>Distance</span><strong>{display(selectedRace.distance)}</strong></div>
        <div className="is-wide"><span>Class</span><strong>{display(selectedRace.raceClass)}</strong></div>
        <div><span>Jump</span><strong>{display(selectedRace.raceTime)}</strong></div>
        <div><span>Declared</span><strong>{selectedRace.runners.length}</strong></div>
      </section>

      <section className="eiq-form-v1__card">
        <header>
          <div>
            <span className="eiq-form-v1__eyebrow">Race {selectedRace.raceNumber}</span>
            <h2>{raceTitle(selectedRace)}</h2>
            <p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p>
          </div>
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
                const tokens = formTokens(runner);
                return [
                  <tr key={`${key}:main`} className={isExpanded ? "is-expanded" : ""}>
                    <td><span className="eiq-form-v1__number">{officialNumber(runner)}</span></td>
                    <td>
                      <div className="eiq-form-v1__runner-cell">
                        <strong>{runnerName(runner)}</strong>
                        <small>{display(runner.official.trainer)}</small>
                      </div>
                    </td>
                    <td>
                      <div className="eiq-form-v1__form-sequence" aria-label={`Last five ${formString(runner)}`}>
                        {tokens.length ? tokens.map((token, tokenIndex) => (
                          <span className={finishTone(token)} key={`${token}-${tokenIndex}`}>{token}</span>
                        )) : <em>—</em>}
                      </div>
                    </td>
                    <td><span className="eiq-form-v1__meta-value">{display(runner.official.barrier)}</span></td>
                    <td><span className="eiq-form-v1__meta-value is-jockey">{display(runner.official.jockey)}</span></td>
                    <td><span className="eiq-form-v1__weight">{display(runner.official.weight)}</span></td>
                    <td><button className="eiq-form-v1__expand" type="button" aria-label={`${isExpanded ? "Collapse" : "Expand"} ${runnerName(runner)} form`} onClick={() => void toggleRunner(runner, index)}>{isExpanded ? "−" : "+"}</button></td>
                  </tr>,
                  isExpanded ? (
                    <tr key={`${key}:detail`} className="eiq-form-v1__detail-row">
                      <td colSpan={7}>
                        {state?.loading ? <p className="eiq-form-v1__message">Loading recent form…</p> : null}
                        {!state?.loading && state?.error ? <p className="eiq-form-v1__message">{state.error}</p> : null}
                        {!state?.loading && !state?.error && runs.length ? (
                          <div className="eiq-form-v1__runs">
                            <div className="eiq-form-v1__runs-title">
                              <div>
                                <span>Recent form</span>
                                <strong>{runnerName(fullRunner)}</strong>
                              </div>
                              <small>{runs.length} latest runs</small>
                            </div>
                            <div className="eiq-form-v1__runs-head"><span>Date</span><span>Track</span><span>Dist.</span><span>Going</span><span>Class</span><span>Finish</span><span>Margin</span><span>Rating</span></div>
                            {runs.map((run, runIndex) => {
                              const record = asRecord(run);
                              const finish = first(record,["finish","position","placing","place"]);
                              const rating = first(record,["rating","wfa","form_rating","performance_rating","figure"]);
                              return <div className="eiq-form-v1__run" key={runIndex}>
                                <span>{first(record,["date","race_date","meeting_date","raceDate"])}</span>
                                <span className="is-track">{first(record,["track","meeting","venue","track_name","meetingName"])}</span>
                                <span>{first(record,["distance","dist","race_distance"])}</span>
                                <span>{first(record,["going","track_condition","trackCondition","condition"])}</span>
                                <span className="is-class">{first(record,["class","race_class","raceClass"])}</span>
                                <span><b className={`eiq-form-v1__finish ${finishTone(finish)}`}>{finish}</b></span>
                                <span>{first(record,["margin","margin_beaten","beaten_margin","beatenMargin"])}</span>
                                <span>{rating !== "-" ? <b className="eiq-form-v1__rating">{rating}</b> : "-"}</span>
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
