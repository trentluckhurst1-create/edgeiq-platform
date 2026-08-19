type RunnerRow = Record<string, any>;

type Props = {
  runners: RunnerRow[];
};

function text(value: unknown): string {
  return String(value ?? "").trim();
}

function hasValue(value: unknown): boolean {
  return text(value) !== "" && text(value) !== "-" && text(value).toUpperCase() !== "NONE";
}

function containsAny(row: RunnerRow, keys: string[]): boolean {
  return keys.some((key) => hasValue(row[key]));
}

export default function IntelligenceCentre({
  runners,
}: Props) {
  const active = runners.filter((row) => !row.isScratched);

  const gearRows = active.filter((row) =>
    containsAny(row, [
      "gearChanges",
      "gear_changes",
      "gear",
    ])
  );

  const stewardRows = active.filter((row) =>
    containsAny(row, [
      "stewards",
      "stewards_comment",
      "stewards_flags",
      "context_flags",
      "handicapperContextFlags",
    ])
  );

  const riskRows = active.filter((row) =>
    containsAny(row, [
      "fakeOverlayRisk",
      "fake_overlay_risk",
      "risk_flags",
      "marketNote",
      "market_note",
    ])
  );

  const contextRows = [...active]
    .filter((row) =>
      gearRows.includes(row) ||
      stewardRows.includes(row) ||
      riskRows.includes(row)
    )
    .slice(0, 10);

  return (
    <div className="edgeiq-intelligence-centre">

      <div className="edgeiq-intelligence-hero">
        <div>
          <div className="edgeiq-kicker">INTELLIGENCE</div>
          <h1>Runner Context Intelligence</h1>
          <p>
            Gear changes, stewards context, risk flags and qualitative signals
            that explain why the model should trust or distrust the market.
          </p>
        </div>

        <div className="edgeiq-intelligence-warning">
          Context is not a tip. It is the reason layer that protects EDGEiQ
          from fake overlays and improves execution judgement.
        </div>
      </div>

      <div className="edgeiq-command-grid">

        <div className="edgeiq-stat-card">
          <div className="label">ACTIVE RUNNERS</div>
          <div className="value emerald">{active.length}</div>
          <div className="sub">current race field</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">GEAR SIGNALS</div>
          <div className="value blue">{gearRows.length}</div>
          <div className="sub">gear changes detected</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">STEWARDS CONTEXT</div>
          <div className="value gold">{stewardRows.length}</div>
          <div className="sub">historical context flags</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">RISK FLAGS</div>
          <div className="value purple">{riskRows.length}</div>
          <div className="sub">fake overlay / market risk</div>
        </div>

      </div>

      <div className="edgeiq-panel">
        <div className="edgeiq-panel-title">
          CONTEXT SIGNAL STACK
        </div>

        <div className="edgeiq-intelligence-table">
          {contextRows.map((row, idx) => (
            <div
              className="edgeiq-intelligence-row"
              key={`${text(row.horse)}-${idx}`}
            >
              <span className="rank">{idx + 1}</span>

              <span className="horse">{text(row.horse) || "UNKNOWN"}</span>

              <span>
                {text(row.gearChanges || row.gear_changes || row.gear) || "-"}
              </span>

              <span>
                {text(
                  row.stewards_flags ||
                  row.context_flags ||
                  row.handicapperContextFlags ||
                  row.stewards_comment
                ) || "-"}
              </span>

              <strong>
                {text(
                  row.fakeOverlayRisk ||
                  row.fake_overlay_risk ||
                  row.risk_flags ||
                  row.marketNote ||
                  row.market_note
                ) || "CLEAR"}
              </strong>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
