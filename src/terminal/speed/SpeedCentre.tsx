type SpeedRow = Record<string, any>;

type Props = {
  speedRows: SpeedRow[];
  paceRows: SpeedRow[];
  selectedMeeting?: string;
  raceDistance?: number | null;
  trackCondition?: string;
};

function text(value: unknown): string {
  return String(value ?? "").trim();
}

function num(value: unknown): number | null {
  const raw = text(value).replace("%", "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export default function SpeedCentre({
  speedRows,
  paceRows,
  selectedMeeting,
  raceDistance,
  trackCondition,
}: Props) {
  const active = speedRows.filter((row) => text(row.is_scratched) !== "1" && text(row.isScratched).toLowerCase() !== "true");

  const leaders = active.filter((row) => {
    const style = text(row.run_style || row.speed_profile || row.map_role || row.position_group).toUpperCase();
    const pos = num(row.map_position || row.predicted_position || row.speed_rank);
    return style.includes("LEAD") || style.includes("PACE") || (pos !== null && pos <= 3);
  });

  const midfield = active.filter((row) => {
    const style = text(row.run_style || row.speed_profile || row.map_role || row.position_group).toUpperCase();
    const pos = num(row.map_position || row.predicted_position || row.speed_rank);
    return style.includes("MID") || (pos !== null && pos > 3 && pos <= 8);
  });

  const backmarkers = active.filter((row) => {
    const style = text(row.run_style || row.speed_profile || row.map_role || row.position_group).toUpperCase();
    const pos = num(row.map_position || row.predicted_position || row.speed_rank);
    return style.includes("BACK") || style.includes("CLOSE") || (pos !== null && pos > 8);
  });

  const pressureCount = paceRows.filter((row) => {
    const pressure = num(row.pressure_score || row.pace_pressure || row.speed_pressure) ?? 0;
    const label = text(row.pressure_label || row.pace_state).toUpperCase();
    return pressure > 0 || label.includes("PRESS");
  }).length;

  return (
    <div className="edgeiq-speed-centre">

      <div className="edgeiq-speed-hero">
        <div>
          <div className="edgeiq-kicker">SPEED MAP</div>
          <h1>Race Shape Intelligence</h1>
          <p>
            Barrier, run style, pace pressure, predicted map position,
            track condition and tactical race-shape context.
          </p>
        </div>

        <div className="edgeiq-speed-context">
          <span>{selectedMeeting || "MEETING"}</span>
          <span>{raceDistance ? `${raceDistance}m` : "DISTANCE TBC"}</span>
          <span>{trackCondition || "CONDITION TBC"}</span>
        </div>
      </div>

      <div className="edgeiq-command-grid">

        <div className="edgeiq-stat-card">
          <div className="label">ACTIVE MAP RUNNERS</div>
          <div className="value emerald">{active.length}</div>
          <div className="sub">excluding scratchings</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">LEAD / PACE</div>
          <div className="value blue">{leaders.length}</div>
          <div className="sub">early speed candidates</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">MIDFIELD</div>
          <div className="value gold">{midfield.length}</div>
          <div className="sub">settle/run-on zone</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">PACE PRESSURE</div>
          <div className="value purple">{pressureCount}</div>
          <div className="sub">{backmarkers.length} backmarkers/closers</div>
        </div>

      </div>
    </div>
  );
}
