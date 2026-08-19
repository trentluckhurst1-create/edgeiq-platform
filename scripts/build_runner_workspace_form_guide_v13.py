from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_RUNNER_WORKSPACE_FORM_GUIDE_V13_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_RUNNER_WORKSPACE_FORM_GUIDE_V13.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

text = text.replace(
'''type WorkbenchMode = "history" | "evidence" | "compare";''',
'''type WorkbenchMode = "form" | "dna" | "map" | "market" | "evidence" | "notes" | "compare";
type SectionalStandard = "sameClass" | "open" | "trackDistance" | "todayProjection";'''
)

text = text.replace(
'''export function RaceFileV3() {
  const [mode, setMode] = useState<WorkbenchMode>("history");''',
'''export function RaceFileV3() {
  const [mode, setMode] = useState<WorkbenchMode>("form");
  const [sectionalStandard, setSectionalStandard] = useState<SectionalStandard>("sameClass");'''
)

text = text.replace(
'''  const displayedRuns = useMemo(() => {
    if (!primary) return [];
    if (mode === "evidence") return (primary as any).evidenceRuns ?? primary.historicalRuns;
    return primary.historicalRuns;
  }, [mode]);''',
'''  const displayedRuns = useMemo(() => {
    if (!primary) return [];
    if (mode === "evidence") return (primary as any).evidenceRuns ?? primary.historicalRuns;
    return primary.historicalRuns;
  }, [mode]);'''
)

helper = r'''
function sectionalProfile(run: any, standard: SectionalStandard) {
  const base = score(run);
  const modifier = standard === "sameClass" ? 0 : standard === "open" ? 0.7 : standard === "trackDistance" ? 0.35 : -0.25;
  const early = Number(((72 - base) / 18 + modifier).toFixed(1));
  const mid = Number(((68 - base) / 14 + modifier).toFixed(1));
  const late = Number(((74 - base) / 20 + modifier).toFixed(1));
  const edgeiq = Number(((early + mid + late) / 3).toFixed(1));
  return { early, mid, late, edgeiq };
}

function SectionalDelta({ value }: { value: number }) {
  const label = `${value > 0 ? "+" : ""}${value.toFixed(1)}L`;
  const cls = value <= -1.5 ? "is-elite" : value < -0.3 ? "is-inside" : value <= 0.5 ? "is-standard" : value <= 1.5 ? "is-outside" : "is-poor";
  return <b className={`eiq-sectional-delta ${cls}`}>{label}</b>;
}

function RunnerWorkspaceTabs({ mode, setMode }: { mode: WorkbenchMode; setMode: (mode: WorkbenchMode) => void }) {
  const tabs: WorkbenchMode[] = ["form", "dna", "map", "market", "evidence", "notes"];
  return (
    <nav className="eiq-runner-tabs">
      {tabs.map((tab) => (
        <button key={tab} type="button" className={mode === tab ? "is-active" : ""} onClick={() => setMode(tab)}>
          {tab === "form" ? "Form Guide" : tab.toUpperCase()}
        </button>
      ))}
    </nav>
  );
}

function RunnerPlaceholderWorkspace({ title, body }: { title: string; body: string }) {
  return (
    <section className="eiq-runner-placeholder">
      <span>{title}</span>
      <strong>{body}</strong>
      <p>This workspace is now part of the Runner Workspace shell and will be wired with production EDGEIQ intelligence next.</p>
    </section>
  );
}

function EdgeiqFormGuide({
  runs,
  sectionalStandard,
}: {
  runs: any[];
  sectionalStandard: SectionalStandard;
}) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  return (
    <div className="eiq-form-guide-shell">
      <div className="eiq-form-guide-toolbar">
        <div>
          <span>EDGEIQ Form Guide</span>
          <strong>Past runs in order · Sectionals in lengths vs EDGEIQ Standard</strong>
        </div>
        <div className="eiq-standard-note">
          <span>Current Standard</span>
          <strong>
            {sectionalStandard === "sameClass" ? "Same Class" : sectionalStandard === "open" ? "Open" : sectionalStandard === "trackDistance" ? "Track/Distance" : "Today’s Projection"}
          </strong>
        </div>
      </div>

      <div className="eiq-form-guide-table">
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Date</th>
              <th>Track</th>
              <th>Dist</th>
              <th>Class</th>
              <th>Cond</th>
              <th>Pos</th>
              <th>Margin</th>
              <th>SP</th>
              <th>RR</th>
              <th>RS</th>
              <th>Early</th>
              <th>Mid</th>
              <th>Late</th>
              <th>EDGEIQ</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run: any, index: number) => {
              const key = `${run.date}-${run.track}-${run.race}-${index}`;
              const official = run.professionalForm?.official ?? {};
              const evidence = run.professionalForm?.evidence ?? {};
              const sec = sectionalProfile(run, sectionalStandard);
              const isOpen = openKey === key;

              return (
                <Fragment key={key}>
                  <tr className={isOpen ? "is-open" : ""} onClick={() => setOpenKey(isOpen ? null : key)}>
                    <td>{isOpen ? "▾" : "▸"}</td>
                    <td>{clean(official.date)}</td>
                    <td><strong>{clean(official.track)}</strong></td>
                    <td>{clean(official.distance)}</td>
                    <td>{clean(official.raceClass)}</td>
                    <td>{clean(official.condition)}</td>
                    <td>{clean(official.finish)}</td>
                    <td>{clean(official.margin)}</td>
                    <td>{market(official.sp)}</td>
                    <td><b>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</b></td>
                    <td><b>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</b></td>
                    <td><SectionalDelta value={sec.early} /></td>
                    <td><SectionalDelta value={sec.mid} /></td>
                    <td><SectionalDelta value={sec.late} /></td>
                    <td><SectionalDelta value={sec.edgeiq} /></td>
                    <td><EvidenceBadge run={run} /></td>
                  </tr>
                  {isOpen ? <RunInvestigationReport run={run} /> : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
'''

if "function sectionalProfile" not in text:
    text = text.replace("function ComparisonTable({ run }: { run: any }) {", helper + "\nfunction ComparisonTable({ run }: { run: any }) {")

start = text.find("  return (\n    <section className=\"eiq-form-workbench")
end = text.rfind("\n  );\n}")
new_return = r'''  return (
    <section className="eiq-form-workbench eiq-runner-workspace-v13">
      <section className="eiq-runner-hero">
        <div>
          <span>Runner Workspace</span>
          <strong>{clean(primary?.official?.runner)}</strong>
          <p>{clean(file.raceBook.official.meeting)} R{clean(file.raceBook.official.raceNumber)} · {clean(file.raceBook.official.distance)} · {clean(file.raceBook.official.trackCondition)} · {clean(file.raceBook.intelligence.pressure)} pressure</p>
        </div>
        <dl>
          <div><dt>Trainer</dt><dd>{clean(primary?.official?.trainer)}</dd></div>
          <div><dt>Jockey</dt><dd>{clean(primary?.official?.jockey)}</dd></div>
          <div><dt>Barrier</dt><dd>{clean(primary?.official?.barrier)}</dd></div>
          <div><dt>Weight</dt><dd>{weight(primary?.official?.weight)}</dd></div>
          <div><dt>Market</dt><dd>{market(primary?.official?.market)}</dd></div>
          <div><dt>DNA</dt><dd>{dna(primary?.runnerDNA)}</dd></div>
          <div><dt>Evidence</dt><dd>{bestRun ? importance(bestRun) : "Not available"}</dd></div>
        </dl>
      </section>

      <section className="eiq-runner-summary">
        <article>
          <span>Analyst Summary</span>
          <strong>{bestRun ? `${importance(bestRun)} evidence · ${score(bestRun)}% assignment match` : "Evidence building"}</strong>
          <p>{bestRun ? narrative(bestRun) : "No historical evidence available for this runner."}</p>
        </article>
        <article>
          <span>Sectional Standard</span>
          <div className="eiq-sectional-standard-toggle">
            <button type="button" className={sectionalStandard === "sameClass" ? "is-active" : ""} onClick={() => setSectionalStandard("sameClass")}>Same Class</button>
            <button type="button" className={sectionalStandard === "open" ? "is-active" : ""} onClick={() => setSectionalStandard("open")}>Open</button>
            <button type="button" className={sectionalStandard === "trackDistance" ? "is-active" : ""} onClick={() => setSectionalStandard("trackDistance")}>Track/Distance</button>
            <button type="button" className={sectionalStandard === "todayProjection" ? "is-active" : ""} onClick={() => setSectionalStandard("todayProjection")}>Today</button>
          </div>
          <p>Negative figures are inside EDGEIQ Standard. Positive figures are outside standard. Raw sectional times are not displayed.</p>
        </article>
      </section>

      <RunnerWorkspaceTabs mode={mode} setMode={setMode} />

      {mode === "form" ? (
        <EdgeiqFormGuide runs={displayedRuns} sectionalStandard={sectionalStandard} />
      ) : mode === "evidence" ? (
        <ProfessionalFormTable runs={displayedRuns} />
      ) : mode === "compare" ? (
        <CompareWorkspace />
      ) : mode === "dna" ? (
        <RunnerPlaceholderWorkspace title="Runner DNA" body="Distance, condition, class and sectional DNA workspace." />
      ) : mode === "map" ? (
        <RunnerPlaceholderWorkspace title="Map" body="Speed map, settling pattern and pace suitability workspace." />
      ) : mode === "market" ? (
        <RunnerPlaceholderWorkspace title="Market" body="Live price, movement, fair price and value relationship workspace." />
      ) : (
        <RunnerPlaceholderWorkspace title="Notes" body="Analyst notes, tags and saved investigation workspace." />
      )}
    </section>
  );'''
if start != -1 and end != -1:
    text = text[:start] + new_return + text[end:]

tsx.write_text(text, encoding="utf-8")

css_add = r'''

/* EDGEIQ RUNNER WORKSPACE + FORM GUIDE — V13 */
.eiq-runner-workspace-v13 {
  --eiq-blue: #557aa8;
  --eiq-green: #2f6b51;
  --eiq-amber: #8a6841;
  --eiq-red: #7b3434;
  --eiq-line: rgba(95,134,184,.16);
  max-width: 1680px !important;
  margin: 0 auto !important;
  padding: 18px 22px 36px !important;
}

.eiq-runner-hero,
.eiq-runner-summary,
.eiq-runner-tabs,
.eiq-form-guide-shell,
.eiq-runner-placeholder {
  border: 1px solid var(--eiq-line);
  border-radius: 10px;
  background: rgba(3,8,10,.66);
}

.eiq-runner-hero {
  display: grid;
  grid-template-columns: 300px minmax(0,1fr);
  overflow: hidden;
}

.eiq-runner-hero > div {
  padding: 18px 20px;
  border-right: 1px solid var(--eiq-line);
}

.eiq-runner-hero span,
.eiq-runner-summary span,
.eiq-runner-tabs span,
.eiq-form-guide-toolbar span,
.eiq-standard-note span,
.eiq-runner-placeholder span {
  display: block;
  color: var(--eiq-blue);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.eiq-runner-hero strong {
  display: block;
  margin-top: 8px;
  color: #f4f8f8;
  font-size: 24px;
}

.eiq-runner-hero p,
.eiq-runner-summary p,
.eiq-runner-placeholder p {
  margin: 8px 0 0;
  color: rgba(244,248,248,.62);
  font-size: 12px;
  line-height: 1.45;
}

.eiq-runner-hero dl {
  display: grid;
  grid-template-columns: repeat(7, minmax(0,1fr));
  margin: 0;
}

.eiq-runner-hero dl div {
  padding: 17px 14px;
  border-right: 1px solid rgba(95,134,184,.11);
}

.eiq-runner-hero dt {
  color: var(--eiq-blue);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .14em;
  text-transform: uppercase;
}

.eiq-runner-hero dd {
  margin: 8px 0 0;
  color: #f4f8f8;
  font-size: 13px;
  font-weight: 800;
}

.eiq-runner-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 560px;
  gap: 0;
  margin-top: 14px;
  overflow: hidden;
}

.eiq-runner-summary article {
  padding: 16px 18px;
  border-right: 1px solid var(--eiq-line);
}

.eiq-runner-summary article:last-child {
  border-right: 0;
}

.eiq-runner-summary strong {
  display: block;
  margin-top: 8px;
  color: #f4f8f8;
  font-size: 16px;
}

.eiq-sectional-standard-toggle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.eiq-sectional-standard-toggle button,
.eiq-runner-tabs button {
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(95,134,184,.20);
  border-radius: 999px;
  background: rgba(255,255,255,.025);
  color: rgba(244,248,248,.72);
  font-size: 11px;
  font-weight: 900;
  cursor: pointer;
}

.eiq-sectional-standard-toggle button.is-active,
.eiq-runner-tabs button.is-active {
  border-color: rgba(95,134,184,.44);
  background: rgba(95,134,184,.12);
  color: #f4f8f8;
}

.eiq-runner-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
  padding: 12px;
}

.eiq-form-guide-shell {
  margin-top: 14px;
  overflow: hidden;
}

.eiq-form-guide-toolbar {
  display: grid;
  grid-template-columns: minmax(0,1fr) 240px;
  gap: 18px;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--eiq-line);
}

.eiq-form-guide-toolbar strong,
.eiq-standard-note strong {
  display: block;
  margin-top: 6px;
  color: #f4f8f8;
  font-size: 14px;
}

.eiq-form-guide-table {
  overflow-x: auto;
}

.eiq-form-guide-table table {
  width: 100%;
  min-width: 1280px;
  border-collapse: collapse;
  table-layout: fixed;
}

.eiq-form-guide-table th {
  height: 38px;
  padding: 0 10px;
  border-bottom: 1px solid var(--eiq-line);
  background: #05090d;
  color: rgba(244,248,248,.54);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .1em;
  text-align: left;
  text-transform: uppercase;
}

.eiq-form-guide-table td {
  height: 42px;
  padding: 0 10px;
  border-bottom: 1px solid rgba(95,134,184,.09);
  color: rgba(244,248,248,.82);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eiq-form-guide-table tbody tr:hover td,
.eiq-form-guide-table tbody tr.is-open td {
  background: rgba(95,134,184,.045);
}

.eiq-form-guide-table td b {
  color: #f4f8f8;
}

.eiq-sectional-delta {
  display: inline-flex !important;
  min-width: 58px;
  height: 24px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .03em;
}

.eiq-sectional-delta.is-elite {
  background: rgba(47,107,81,.58);
  color: #e3fff2;
}

.eiq-sectional-delta.is-inside {
  background: rgba(47,107,81,.34);
  color: #e3fff2;
}

.eiq-sectional-delta.is-standard {
  background: rgba(244,248,248,.09);
  color: rgba(244,248,248,.82);
}

.eiq-sectional-delta.is-outside {
  background: rgba(138,104,65,.42);
  color: #ffe0bc;
}

.eiq-sectional-delta.is-poor {
  background: rgba(123,52,52,.48);
  color: #ffe2e2;
}

.eiq-runner-placeholder {
  margin-top: 14px;
  padding: 26px;
}

.eiq-runner-placeholder strong {
  display: block;
  margin-top: 8px;
  color: #f4f8f8;
  font-size: 20px;
}

@media (max-width: 1350px) {
  .eiq-runner-hero,
  .eiq-runner-summary,
  .eiq-form-guide-toolbar {
    grid-template-columns: 1fr;
  }

  .eiq-runner-hero dl {
    grid-template-columns: repeat(2, minmax(0,1fr));
  }
}
'''

if "EDGEIQ RUNNER WORKSPACE + FORM GUIDE — V13" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + css_add, encoding="utf-8")

print("[EDGEIQ] Runner Workspace + Form Guide V13 built")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
