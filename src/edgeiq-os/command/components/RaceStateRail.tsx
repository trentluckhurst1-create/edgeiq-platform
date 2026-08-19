import type { EdgeiqRaceContext } from "../../services/race-context";

type RaceStateRailProps = {
  raceContext: EdgeiqRaceContext;
};

export function RaceStateRail({ raceContext }: RaceStateRailProps) {
  const raceStateItems = [
    ["Feed", raceContext.feedHealth, "Live intelligence available", "good"],
    ["Track", raceContext.trackCondition, "Stable surface profile", "neutral"],
    ["Rail", raceContext.railPosition.replace("Rail ", ""), "No confirmed pattern", "info"],
    ["Weather", raceContext.weather.state, raceContext.weather.detail, "neutral"],
    ["Clock", "12 min", "Race state active", "monitor"],
    ["Updated", raceContext.updatedAt, raceContext.raceTime, "neutral"],
  ];

  return (
    <aside className="eiq-command-live__rail">
      <h2>System State</h2>
      {raceStateItems.map(([label, value, detail, tone]) => (
        <div className="eiq-command-live__rail-item" key={label}>
          <span>{label}</span>
          <strong className={`is-${tone}`}>{value}</strong>
          {detail ? <p>{detail}</p> : null}
        </div>
      ))}
    </aside>
  );
}
