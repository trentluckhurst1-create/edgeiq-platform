type RunnerRow = Record<string, any>;
type FormRow = Record<string, any>;

type Props = {
  runners: RunnerRow[];
  selectedHorse?: string;
  selectedHistory?: FormRow[];
  selectedFullCareer?: FormRow[];
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

export default function FormCentre({
  runners,
  selectedHorse,
  selectedHistory = [],
  selectedFullCareer = [],
}: Props) {
  const active = runners.filter((row) => !row.isScratched);
  const officialRecent = selectedHistory.filter((row) => {
    const type = text(row.runType || row.run_type).toUpperCase();
    const official = row.isOfficialRace;
    return official === true || type === "RACE" || type === "";
  });

  const trials = selectedHistory.filter((row) => {
    const type = text(row.runType || row.run_type).toUpperCase();
    return type.includes("TRIAL") || type.includes("JUMPOUT");
  });

  const ratings = officialRecent
    .map((row) => num(row.runRating || row.run_rating))
    .filter((value): value is number => value !== null);

  const peak = ratings.length ? Math.max(...ratings) : null;
  const avg = ratings.length
    ? ratings.reduce((sum, value) => sum + value, 0) / ratings.length
    : null;

  return (
    <div className="edgeiq-form-centre">

      <div className="edgeiq-form-hero">
        <div>
          <div className="edgeiq-kicker">FORM</div>
          <h1>Runner Form Intelligence</h1>
          <p>
            Last-start profile, full career evidence, official race ratings,
            trials/jumpouts and historical context for the selected runner.
          </p>
        </div>

        <div className="edgeiq-form-selected">
          <span>SELECTED</span>
          <strong>{selectedHorse || "NO RUNNER SELECTED"}</strong>
        </div>
      </div>

      <div className="edgeiq-command-grid">

        <div className="edgeiq-stat-card">
          <div className="label">FIELD RUNNERS</div>
          <div className="value emerald">{active.length}</div>
          <div className="sub">current active field</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">RECENT FORM</div>
          <div className="value blue">{selectedHistory.length}</div>
          <div className="sub">loaded recent runs</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">OFFICIAL RUNS</div>
          <div className="value gold">{officialRecent.length}</div>
          <div className="sub">{trials.length} trials/jumpouts</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">RATING PROFILE</div>
          <div className="value purple">
            {peak === null ? "-" : peak.toFixed(1)}
          </div>
          <div className="sub">
            avg {avg === null ? "-" : avg.toFixed(1)}
          </div>
        </div>

      </div>
    </div>
  );
}
