from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_VERDICT_ENGINE_V10_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_VERDICT_ENGINE_V10_20260709.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

insert_after = '''function MatchBar({ value }: { value: number }) {
  const width = Math.max(4, Math.min(100, value));
  return (
    <div className="eiq-match-bar">
      <i style={{ width: `${width}%` }} />
      <strong>{value}%</strong>
    </div>
  );
}
'''

addition = r'''
function VerdictPanel({ run }: { run: any }) {
  const match = score(run);
  const level = quality(run);
  const role = importance(run);
  const positives = reasons(run).slice(0, 3);
  const risks = changes(run).slice(0, 3);

  return (
    <section className="eiq-verdict-panel">
      <div>
        <span>EDGEIQ Verdict</span>
        <strong>{role === "PRIMARY" ? "Anchor this run in the assessment." : role === "SUPPORTING" ? "Use this as supporting evidence." : "Use this as context only."}</strong>
        <p>
          {match}% assignment match. Evidence quality is {level.toLowerCase()}. This historical run helps explain the runner, but should be tested against the comparison factors before forming a final view.
        </p>
      </div>

      <aside>
        <span>Evidence Match</span>
        <MatchBar value={match} />
        <b>{role}</b>
      </aside>

      <article>
        <span>Best Support</span>
        <ul>{positives.map((x) => <li key={x}>✓ {x}</li>)}</ul>
      </article>

      <article>
        <span>Main Risks</span>
        <ul>{risks.map((x) => <li key={x}>⚠ {x}</li>)}</ul>
      </article>
    </section>
  );
}

function FactorScorePanel({ run }: { run: any }) {
  const evidence = run.professionalForm?.evidence ?? {};
  const rows = [
    ["Race Strength", evidence.raceStrength?.overall ?? run.edgeiqRaceStrength, "+", "Strong historical reference"],
    ["Run Rating", evidence.runRating?.overall ?? run.edgeiqRunRating, "+", "Performance quality"],
    ["Pressure", evidence.pressure, "+", "Pressure profile"],
    ["Tempo", evidence.tempo, "+", "Race speed profile"],
    ["Barrier", run.professionalForm?.official?.barrier, "±", "Needs comparison"],
    ["Track", run.professionalForm?.official?.condition, "±", "Condition transfer"],
  ];

  return (
    <section className="eiq-factor-score-panel">
      <span>Evidence Score Breakdown</span>
      <table>
        <thead>
          <tr><th>Factor</th><th>Value</th><th>Impact</th><th>Reason</th></tr>
        </thead>
        <tbody>
          {rows.map(([factor, value, impact, reason]) => (
            <tr key={factor}>
              <td>{factor}</td>
              <td>{clean(value)}</td>
              <td><b className={impact === "+" ? "is-plus" : "is-watch"}>{impact}</b></td>
              <td>{reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
'''

if addition.strip() not in text:
    text = text.replace(insert_after, insert_after + "\n" + addition)

text = text.replace(
'''          <ComparisonTable run={run} />

          <section className="eiq-official-record">''',
'''          <ComparisonTable run={run} />

          <FactorScorePanel run={run} />

          <VerdictPanel run={run} />

          <section className="eiq-official-record">'''
)

tsx.write_text(text, encoding="utf-8")

css_add = r'''

/* EDGEIQ VERDICT ENGINE — V10 */
.eiq-factor-score-panel,
.eiq-verdict-panel {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid rgba(95,134,184,.14);
  background: rgba(255,255,255,.018);
}

.eiq-factor-score-panel table {
  width: 100%;
  margin-top: 12px;
  border-collapse: collapse;
}

.eiq-factor-score-panel th,
.eiq-factor-score-panel td {
  height: 34px;
  border-bottom: 1px solid rgba(95,134,184,.10);
  color: rgba(244,248,248,.78);
  font-size: 12px;
  text-align: left;
}

.eiq-factor-score-panel th {
  color: rgba(244,248,248,.48);
  font-size: 10px;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.eiq-factor-score-panel b {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 22px;
  border-radius: 999px;
  font-size: 12px;
}

.eiq-factor-score-panel b.is-plus {
  background: rgba(36,92,67,.32);
  color: #d8fff0;
}

.eiq-factor-score-panel b.is-watch {
  background: rgba(107,75,48,.28);
  color: #ffe0bc;
}

.eiq-verdict-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) 230px 1fr 1fr;
  gap: 14px;
  border-left: 3px solid rgba(95,134,184,.72);
}

.eiq-verdict-panel > div,
.eiq-verdict-panel > aside,
.eiq-verdict-panel > article {
  min-width: 0;
  padding-right: 14px;
  border-right: 1px solid rgba(95,134,184,.10);
}

.eiq-verdict-panel > article:last-child {
  border-right: 0;
}

.eiq-verdict-panel strong {
  display: block;
  margin-top: 8px;
  font-size: 18px;
  line-height: 1.25;
}

.eiq-verdict-panel aside b {
  display: inline-flex;
  margin-top: 10px;
  height: 24px;
  padding: 0 9px;
  align-items: center;
  border-radius: 999px;
  background: rgba(95,134,184,.16);
  color: #f4f8f8;
  font-size: 10px;
  letter-spacing: .1em;
}

.eiq-verdict-panel ul {
  display: grid;
  gap: 7px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  color: rgba(244,248,248,.72);
  font-size: 12px;
  line-height: 1.35;
}

@media (max-width: 1350px) {
  .eiq-verdict-panel {
    grid-template-columns: 1fr;
  }

  .eiq-verdict-panel > div,
  .eiq-verdict-panel > aside,
  .eiq-verdict-panel > article {
    border-right: 0;
    padding-right: 0;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(95,134,184,.10);
  }
}
'''

if "EDGEIQ VERDICT ENGINE — V10" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + css_add, encoding="utf-8")

print("[EDGEIQ] Verdict Engine V10 built")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
