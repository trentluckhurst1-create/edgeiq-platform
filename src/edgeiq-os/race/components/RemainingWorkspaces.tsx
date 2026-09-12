import { useMemo } from "react";
import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";

type RaceWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

function display(value: unknown, fallback = "-"): string {
  return cleanProductText(value, fallback);
}

function useSelectedRace(meeting: ThreeDayMeeting | null, selectedRaceKey: string | null): ThreeDayRace | null {
  return useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);
}

function RaceTabs({ meeting, race, onRaceChange }: { meeting: ThreeDayMeeting; race: ThreeDayRace; onRaceChange: (raceKey: string) => void }) {
  return (
    <nav className="eiq-build-v1__race-tabs" aria-label="Meeting races">
      {meeting.races.map((item) => (
        <button key={item.raceKey} type="button" className={item.raceKey === race.raceKey ? "is-active" : ""} onClick={() => onRaceChange(item.raceKey)}>
          <strong>R{item.raceNumber}</strong><span>{display(item.raceTime)}</span>
        </button>
      ))}
    </nav>
  );
}

function RaceHeader({ title, meeting, race }: { title: string; meeting: ThreeDayMeeting; race: ThreeDayRace }) {
  return (
    <header className="eiq-build-v1__header">
      <div><p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p><h1>{title}</h1></div>
      <strong>R{race.raceNumber}</strong>
    </header>
  );
}

function EmptyCell() { return <span className="eiq-build-v1__dash">-</span>; }

export function InsightsWorkspace({ meeting, selectedRaceKey, onRaceChange }: RaceWorkspaceProps) {
  const race = useSelectedRace(meeting, selectedRaceKey);
  if (!meeting || !race) return null;
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="INSIGHTS">
      <RaceHeader title="Insights" meeting={meeting} race={race} />
      <RaceTabs meeting={meeting} race={race} onRaceChange={onRaceChange} />
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2">
        {['Key Angles','Race Shape','Price & Edge','Risk Flags'].map((title) => <article className="eiq-build-v1__card" key={title}><h2>{title}</h2><EmptyCell /></article>)}
      </div>
    </section>
  );
}

export function ResultsWorkspace({ meeting, selectedRaceKey, onRaceChange }: RaceWorkspaceProps) {
  const race = useSelectedRace(meeting, selectedRaceKey);
  if (!meeting || !race) return null;
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="RESULTS">
      <RaceHeader title="Results" meeting={meeting} race={race} />
      <RaceTabs meeting={meeting} race={race} onRaceChange={onRaceChange} />
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>{display(race.raceName, `Race ${race.raceNumber}`)}</h2></header><table><thead><tr><th>POS.</th><th>RUNNER</th><th>JOCKEY</th><th>SP</th><th>MARGIN</th><th>TIME</th></tr></thead><tbody><tr><td colSpan={6} className="eiq-build-v1__empty">-</td></tr></tbody></table></section>
    </section>
  );
}

export function ReviewWorkspace({ meeting, selectedRaceKey, onRaceChange }: RaceWorkspaceProps) {
  const race = useSelectedRace(meeting, selectedRaceKey);
  if (!meeting || !race) return null;
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="REVIEW">
      <RaceHeader title="Review" meeting={meeting} race={race} />
      <RaceTabs meeting={meeting} race={race} onRaceChange={onRaceChange} />
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2">
        {['Race Review','Model vs Outcome','Market Review','Notes'].map((title) => <article className="eiq-build-v1__card" key={title}><h2>{title}</h2><EmptyCell /></article>)}
      </div>
    </section>
  );
}

export function ResearchLabWorkspace() {
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="RESEARCH-LAB">
      <header className="eiq-build-v1__header"><div><p>EDGEiQ / RACING</p><h1>Research Lab</h1></div></header>
      <div className="eiq-build-v1__grid eiq-build-v1__grid--3">
        {['Dataset','Experiment','Model'].map((title) => <article className="eiq-build-v1__card" key={title}><h2>{title}</h2><EmptyCell /></article>)}
      </div>
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>Experiment Queue</h2></header><table><thead><tr><th>ID</th><th>EXPERIMENT</th><th>SCOPE</th><th>STATUS</th><th>RESULT</th></tr></thead><tbody><tr><td colSpan={5} className="eiq-build-v1__empty">-</td></tr></tbody></table></section>
    </section>
  );
}

export function CompareWorkspace() {
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="COMPARE">
      <header className="eiq-build-v1__header"><div><p>EDGEiQ / RACING</p><h1>Compare</h1></div></header>
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2"><article className="eiq-build-v1__card"><h2>Selection A</h2><EmptyCell /></article><article className="eiq-build-v1__card"><h2>Selection B</h2><EmptyCell /></article></div>
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>Comparison Matrix</h2></header><table><thead><tr><th>METRIC</th><th>SELECTION A</th><th>SELECTION B</th><th>DIFF.</th></tr></thead><tbody><tr><td colSpan={4} className="eiq-build-v1__empty">-</td></tr></tbody></table></section>
    </section>
  );
}

export function SettingsWorkspace() {
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="SETTINGS">
      <header className="eiq-build-v1__header"><div><p>EDGEiQ / RACING</p><h1>Settings</h1></div></header>
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2">
        {['Data Feeds','Display','Race Defaults','Workspace'].map((title) => <article className="eiq-build-v1__card eiq-build-v1__settings-card" key={title}><h2>{title}</h2><dl><div><dt>Status</dt><dd>-</dd></div><div><dt>Default</dt><dd>-</dd></div></dl></article>)}
      </div>
    </section>
  );
}
