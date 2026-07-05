type Row = Record<string, any>;
type StatsMode = "JOCKEYS" | "TRAINERS";

type EnrichedRunnerLike = {
  row: Row;
  bet?: Row;
  runnerHistory?: Row[];
  [key: string]: any;
};

type RaceStatsWorkspaceProps = {
  activeRaceRows: EnrichedRunnerLike[];
  statsMode: StatsMode;
  setStatsMode: (value: StatsMode) => void;
  header: Row;

  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  cleanHorse: (value: unknown) => string;
  historyRatingValue: (row: Row | undefined) => number | null;
  historyFinishText: (row: Row | undefined) => string;
  integer: (value: unknown) => number | null;
  edgePct: (row: Row, bet?: Row) => number | null;
  trackCondition: (row: Row) => string;
  distance: (row: Row) => string;
  raceClass: (row: Row) => string;
  paceMapRole: (item: EnrichedRunnerLike) => string;
  isScratched: (item: EnrichedRunnerLike) => boolean;
  track: (row: Row) => string;
  pct: (value: number | null) => string;
  renderMetricValue: (value: number | null, digits?: number, signedMode?: boolean) => string;
  runnerRowKey: (row: Row) => string;
  saddle: (row: Row) => number;
  horse: (row: Row) => string;
  projectionRatingValue: (item: EnrichedRunnerLike) => number | null;
};

export function RaceStatsWorkspace(props: RaceStatsWorkspaceProps) {
  const {
    activeRaceRows,
    statsMode,
    setStatsMode,
    header,
    firstText,
    cleanHorse,
    historyRatingValue,
    historyFinishText,
    integer,
    edgePct,
    trackCondition,
    distance,
    raceClass,
    paceMapRole,
    isScratched,
    track,
    pct,
    renderMetricValue,
    runnerRowKey,
    saddle,
    horse,
    projectionRatingValue,
  } = props;

  const empty = "-";
  const entityLabel = statsMode === "TRAINERS" ? "TRAINERS" : "JOCKEYS";
  const entityDisplay = statsMode === "TRAINERS" ? "Trainer" : "Jockey";

  const entityNameFor = (item: EnrichedRunnerLike) =>
    firstText(item.row, statsMode === "TRAINERS" ? ["trainer", "trainer_name"] : ["jockey", "jockey_name", "rider"], "Unknown");

  const statsGroups = activeRaceRows.reduce<Record<string, EnrichedRunnerLike[]>>((acc, item) => {
    const name = entityNameFor(item);
    const key = cleanHorse(name);
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  const statsGroupEntries = Object.entries(statsGroups).map(([key, rows]) => {
    const allRuns = rows.flatMap((item) => item.runnerHistory || []);
    const rated = allRuns.map((run) => historyRatingValue(run)).filter((value): value is number => value !== null);
    const wins = allRuns.filter((run) => /^1(ST)?$/i.test(historyFinishText(run))).length;
    const places = allRuns.filter((run) => {
      const pos = integer(historyFinishText(run));
      return pos !== null && pos <= 3;
    }).length;
    const starts = allRuns.length || rows.length;
    const winRate = starts ? (wins / starts) * 100 : null;
    const placeRate = starts ? (places / starts) * 100 : null;
    const avgRating = rated.length ? rated.reduce((sum, value) => sum + value, 0) / rated.length : null;
    const edgeAverage = rows.map((row) => edgePct(row.row, row.bet)).filter((value): value is number => value !== null);
    const roi = edgeAverage.length ? edgeAverage.reduce((sum, value) => sum + value, 0) / edgeAverage.length : null;
    return { key, name: entityNameFor(rows[0]), rows, starts, wins, places, winRate, placeRate, avgRating, roi };
  }).sort((a, b) => (b.avgRating ?? -999) - (a.avgRating ?? -999));

  const activeStatsEntity = statsGroupEntries[0] || null;
  const statRaceRows = activeStatsEntity?.rows || activeRaceRows.slice(0, 5);

  const statsRecentCards = [
    ["Last 10 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
    ["Last 25 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
    ["Last 50 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
    ["Last 100 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
  ] as const;

  const statsProfileRows = [
    ["Flemington", activeStatsEntity?.starts ?? activeRaceRows.length, activeStatsEntity?.wins ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.roi ?? null],
    [trackCondition(header), activeStatsEntity?.starts ?? activeRaceRows.length, activeStatsEntity?.places ?? 0, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
    [distance(header), statRaceRows.length, statRaceRows.filter((item) => paceMapRole(item) === "LEADER").length, activeStatsEntity?.winRate ?? null, activeStatsEntity?.roi ?? null],
    [raceClass(header), statRaceRows.length, statRaceRows.filter((item) => !isScratched(item)).length, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
  ] as const;

  const statsStyleRows = ["LEADER", "ON PACE", "MIDFIELD", "BACKMARKER"].map((style) => {
    const count = activeRaceRows.filter((item) => paceMapRole(item) === style).length;
    return [style, count, activeRaceRows.length ? (count / activeRaceRows.length) * 100 : null] as const;
  });

  return (
    <section className="edgeiq-stats-tab edgeiq-product-section edgeiq-stats-lock">
      <div className="edgeiq-stats-toolbar">
        <div>
          <span>STATS</span>
          <strong>{entityLabel}</strong>
          <em>Deep analytics and performance profiling for {entityLabel.toLowerCase()}.</em>
        </div>
        <div className="edgeiq-stats-switch">
          {(["JOCKEYS", "TRAINERS"] as StatsMode[]).map((mode) => (
            <button type="button" key={`stats-mode-${mode}`} className={statsMode === mode ? "is-active" : ""} onClick={() => setStatsMode(mode)}>
              {mode}
            </button>
          ))}
        </div>
      </div>

      <div className="edgeiq-stats-grid">
        <section className="edgeiq-stats-main">
          <header className="edgeiq-stats-profile">
            <div className="edgeiq-stats-avatar">{statsMode === "TRAINERS" ? "T" : "J"}</div>
            <div>
              <strong>{activeStatsEntity?.name || (statsMode === "TRAINERS" ? "Trainer Profile" : "Jockey Profile")}</strong>
              <span>Top rated {entityDisplay.toLowerCase()}</span>
              <em>{track(header)} / {distance(header)} / {raceClass(header)}</em>
            </div>
            <div className="edgeiq-stats-season">
              {[["Starts", activeStatsEntity?.starts ?? 0], ["Wins", activeStatsEntity?.wins ?? 0], ["Places", activeStatsEntity?.places ?? 0], ["Win %", activeStatsEntity?.winRate ?? null], ["Place %", activeStatsEntity?.placeRate ?? null], ["ROI", activeStatsEntity?.roi ?? null]].map(([label, value]) => (
                <span key={`stats-season-${label}`}>
                  <b>{label}</b>
                  <strong>{typeof value === "number" ? (String(label).includes("%") || label === "ROI" ? pct(value) : String(value)) : empty}</strong>
                </span>
              ))}
            </div>
          </header>

          <div className="edgeiq-stats-recent">
            {statsRecentCards.map(([label, wins, places, winRate, placeRate, roi]) => (
              <article key={`stats-card-${label}`}>
                <span>{label}</span>
                <strong>{wins}</strong><em>Wins</em>
                <strong>{places}</strong><em>Places</em>
                <b>{typeof winRate === "number" ? pct(winRate) : empty}</b>
                <small>ROI {typeof roi === "number" ? pct(roi) : empty}</small>
              </article>
            ))}
          </div>

          <div className="edgeiq-stats-two">
            <section className="edgeiq-stats-panel">
              <strong>Performance by {statsMode === "TRAINERS" ? "Track / Class" : "Barrier / Track"}</strong>
              <div className="edgeiq-stats-table">
                {statsProfileRows.map(([label, starts, wins, winRate, roi]) => (
                  <div key={`stats-profile-${label}`}>
                    <span>{label}</span><em>{starts}</em><em>{wins}</em>
                    <b>{typeof winRate === "number" ? pct(winRate) : empty}</b>
                    <b>{typeof roi === "number" ? pct(roi) : empty}</b>
                  </div>
                ))}
              </div>
            </section>

            <section className="edgeiq-stats-panel">
              <strong>Run Style Match-ups</strong>
              <div className="edgeiq-stats-bars">
                {statsStyleRows.map(([label, count, rate]) => (
                  <div key={`stats-style-${label}`}>
                    <span>{label}</span>
                    <i><b style={{ width: `${Math.max(8, Number(rate) || 0)}%` }} /></i>
                    <em>{count}</em>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="edgeiq-stats-panel">
            <strong>{statsMode === "TRAINERS" ? "Upcoming Runners" : "Current Race Rides"}</strong>
            <div className="edgeiq-stats-runners">
              {statRaceRows.slice(0, 8).map((item) => (
                <div key={`stats-runner-${runnerRowKey(item.row)}`}>
                  <span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span>
                  <strong>{horse(item.row)}</strong>
                  <em>{firstText(item.row, ["jockey", "jockey_name", "rider"], "-")}</em>
                  <em>{firstText(item.row, ["trainer", "trainer_name"], "-")}</em>
                  <b>{renderMetricValue(projectionRatingValue(item), 1)}</b>
                </div>
              ))}
            </div>
          </section>
        </section>

        <aside className="edgeiq-stats-side">
          <section>
            <strong>{entityDisplay} Profile Summary</strong>
            <div className="edgeiq-stats-radar"><i /></div>
            {[["Win Rate", activeStatsEntity?.winRate], ["Place Rate", activeStatsEntity?.placeRate], ["Consistency", activeStatsEntity?.avgRating], ["Market Perf.", activeStatsEntity?.roi], ["Overall Score", activeStatsEntity?.avgRating]].map(([label, value]) => (
              <div key={`stats-summary-${label}`}>
                <span>{label}</span>
                <em>{typeof value === "number" ? (String(label).includes("Rate") || String(label).includes("Perf") ? pct(value) : renderMetricValue(value, 1)) : empty}</em>
              </div>
            ))}
          </section>

          <section>
            <strong>Top Tracks</strong>
            {statsGroupEntries.slice(0, 5).map((entry) => (
              <div key={`stats-top-${entry.key}`}>
                <span>{entry.name}</span>
                <i><b style={{ width: `${Math.max(10, Math.min(100, entry.avgRating ?? 0))}%` }} /></i>
                <em>{entry.avgRating === null ? empty : renderMetricValue(entry.avgRating, 1)}</em>
              </div>
            ))}
          </section>

          <section>
            <strong>Key Insights</strong>
            <p>{activeStatsEntity ? `${activeStatsEntity.name} profiles strongest around ${track(header)} with ${activeStatsEntity.starts} available starts in the terminal sample.` : "Stats profile will populate when runner context is available."}</p>
            <p>Figures are research context only and do not alter ratings or production prices.</p>
          </section>
        </aside>
      </div>
    </section>
  );
}
