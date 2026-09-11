import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { loadRunnerDetail } from "../services/runnerDetailFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";

type SpeedMapWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

type MapLane = "Leader" | "On Pace" | "Midfield" | "Back" | "Unmapped";
type MapRunner = { runner: ThreeDayRunner; lane: MapLane; rawPosition: string };

function display(value: unknown, fallback = "-"): string { return cleanProductText(value, fallback); }
function officialNumber(runner: ThreeDayRunner): string { return display(runner.official.no ?? runner.official.number); }
function runnerName(runner: ThreeDayRunner): string { return display(runner.official.runner, "Unnamed runner"); }
function raceTitle(race: ThreeDayRace): string { return display(race.raceName, `Race ${race.raceNumber}`); }
function detailPath(runner: ThreeDayRunner): string { const value = runner.source?.runnerDetailPath; return typeof value === "string" ? value : ""; }

const POSITION_KEYS = ["map_position", "mapPosition", "pace_position", "pacePosition", "settling_position", "settlingPosition", "settling", "run_style", "runStyle"];

function explicitPosition(runner: ThreeDayRunner): string {
  const source = runner.source ?? {};
  for (const key of POSITION_KEYS) {
    const value = String(source[key] ?? "").trim();
    if (value) return value;
  }
  return "";
}

function laneFor(value: string): MapLane {
  const text = value.toLowerCase();
  if (/leader|lead|front|pace.?maker/.test(text)) return "Leader";
  if (/on.?pace|prominent|forward/.test(text)) return "On Pace";
  if (/mid|middle/.test(text)) return "Midfield";
  if (/back|rear|settle.?back|closer/.test(text)) return "Back";
  return "Unmapped";
}

export function SpeedMapWorkspace({ meeting, selectedRaceKey, onRaceChange }: SpeedMapWorkspaceProps) {
  const selectedRace = useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);

  const [rows, setRows] = useState<MapRunner[]>([]);
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
      const rawPosition = explicitPosition(fullRunner);
      return { runner: fullRunner, lane: laneFor(rawPosition), rawPosition } satisfies MapRunner;
    })).then((next) => {
      if (!active) return;
      next.sort((a,b) => Number(a.runner.official.barrier ?? 999) - Number(b.runner.official.barrier ?? 999));
      setRows(next);
      setLoading(false);
    });
    return () => { active = false; };
  }, [selectedRace]);

  if (!meeting || !selectedRace) return null;
  const lanes: MapLane[] = ["Leader", "On Pace", "Midfield", "Back", "Unmapped"];

  return (
    <section className="eiq-map-v1" aria-label="Speed Map workspace" data-edgeiq-workspace-key="SPEED_MAP">
      <header className="eiq-map-v1__header"><div><p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p><h1>Speed Map</h1></div><strong>{selectedRace.runners.length} runners</strong></header>
      <nav className="eiq-map-v1__race-tabs" aria-label="Meeting races">{meeting.races.map((race) => <button key={race.raceKey} type="button" className={race.raceKey === selectedRace.raceKey ? "is-active" : ""} onClick={() => onRaceChange(race.raceKey)}><strong>R{race.raceNumber}</strong><span>{display(race.raceTime)}</span></button>)}</nav>
      <section className="eiq-map-v1__card">
        <header><div><h2>{raceTitle(selectedRace)}</h2><p>{display(selectedRace.distance)} · {display(selectedRace.raceClass)}</p></div><strong>{loading ? "Loading…" : `${rows.filter((row) => row.lane !== "Unmapped").length} mapped`}</strong></header>
        <div className="eiq-map-v1__lanes">
          {lanes.map((lane) => <section key={lane} className={`eiq-map-v1__lane is-${lane.toLowerCase().replace(/\s+/g,"-")}`}><header><strong>{lane}</strong><span>{rows.filter((row) => row.lane === lane).length}</span></header><div>{rows.filter((row) => row.lane === lane).map((row) => <article key={`${officialNumber(row.runner)}-${runnerName(row.runner)}`}><span className="eiq-map-v1__barrier">B{display(row.runner.official.barrier)}</span><div><strong>{officialNumber(row.runner)}. {runnerName(row.runner)}</strong><small>{row.rawPosition || "-"}</small></div></article>)}</div></section>)}
        </div>
      </section>
    </section>
  );
}
