type Row = Record<string, any>;

type RaceTrackWorkspaceProps = {
  header: Row;
  activeRaceRows: any[];
  railDisplay: string;
  track: (row: Row) => string;
  distance: (row: Row) => string;
  trackCondition: (row: Row) => string;
  raceNo: (row: Row) => string;
};

export function RaceTrackWorkspace(props: RaceTrackWorkspaceProps) {
  const { header, activeRaceRows, railDisplay, track, distance, trackCondition, raceNo } = props;

  return (
    <section className="edgeiq-track-tab edgeiq-product-section edgeiq-product-v4-panel">
      <div className="edgeiq-tab-heading edgeiq-product-v4-section-title">
        <span>TRACK</span>
        <strong>Track Profile</strong>
        <em>Track map, rail and race-day profile.</em>
      </div>
      <div className="edgeiq-product-v4-fact-grid">
        {[
          ["Track", track(header)],
          ["Distance", distance(header)],
          ["Condition", trackCondition(header)],
          ["Rail", railDisplay],
          ["Race", `R${raceNo(header)}`],
          ["Runners", String(activeRaceRows.length)],
        ].map(([label, value]) => (
          <article key={`track-v4-${label}`}>
            <span>{label}</span>
            <strong>{value && value !== "-" ? value : "Pending"}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}
