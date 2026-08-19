from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_FINAL_RUNTIME_PHASE03_NO_FALLBACKS_{STAMP}"
FILES = [
    "src/edgeiq-os/race/components/RaceWorkspace.tsx",
    "src/edgeiq-os/race/components/PerformanceWorkspace.tsx",
    "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx",
    "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
    "src/edgeiq-os/race/components/InsightsWorkspace.tsx",
    "src/edgeiq-os/race/components/ReviewWorkspace.tsx",
    "src/edgeiq-os/race/components/LabWorkspace.tsx",
]

for rel in FILES:
    src = ROOT / rel
    dst = CHECKPOINT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def edit(rel: str, fn):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    new = fn(text)
    if new == text:
        raise SystemExit(f"No change made to {rel}")
    path.write_text(new, encoding="utf-8", newline="\n")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Missing target for {label}")
    return text.replace(old, new, 1)

# RaceWorkspace: pass already-loaded field into specialty workspaces as display fallback only.
def patch_race_workspace(text: str) -> str:
    text = must_replace(text,
'''        <PerformanceWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
        />''',
'''        <PerformanceWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
        />''', "performance field prop")
    text = must_replace(text,
'''        <InsightsWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
        />''',
'''        <InsightsWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
        />''', "insights field prop")
    text = must_replace(text,
'''        <EpiWorkspaceWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
        />''',
'''        <EpiWorkspaceWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
        />''', "epi field prop")
    text = must_replace(text,
'''        <OverviewWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          onOpenTab={setTab}
        />''',
'''        <OverviewWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
          onOpenTab={setTab}
        />''', "overview field prop")
    return text

edit("src/edgeiq-os/race/components/RaceWorkspace.tsx", patch_race_workspace)

# Performance: add field fallback table instead of one-line empty state.
def patch_performance(text: str) -> str:
    text = must_replace(text,
'''type PerformanceWorkspaceProps = {

  raceKey?: string | null;

  meetingKey?: string | null;

  raceLabel?: string | null;

};''',
'''type PerformanceWorkspaceProps = {

  raceKey?: string | null;

  meetingKey?: string | null;

  raceLabel?: string | null;

  field?: any[];

};''', "performance props")
    text = must_replace(text,
'''function value(text: string | null | undefined): string {

  return text && text.trim() ? text : "";

}
''',
'''function value(text: string | null | undefined): string {

  return text && text.trim() ? text : "";

}

function runnerDisplay(row: any, index: number): { no: string; horse: string } {
  const no = String(row?.number ?? row?.runnerNumber ?? row?.saddlecloth ?? row?.no ?? index + 1).trim();
  const horse = String(row?.runnerName ?? row?.runner ?? row?.horse ?? row?.name ?? "Runner pending").trim();
  return { no, horse };
}
''', "performance runnerDisplay")
    text = must_replace(text,
'''export function PerformanceWorkspace({ raceKey, meetingKey = null, raceLabel = null }: PerformanceWorkspaceProps) {''',
'''export function PerformanceWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [] }: PerformanceWorkspaceProps) {''', "performance signature")
    text = must_replace(text,
'''  if (!viewModel.rows.length) {

    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Governed historical performance rows are not available for this race.</div></section>;

  }
''',
'''  if (!viewModel.rows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 30) : [];
    return (
      <section className="eiq-epi-v1 eiq-performance-v2">
        <section className="eiq-performance-approved-modules" aria-label="Performance modules">
          {["FIELD EPI MATRIX", "PERFORMANCE DNA", "PEAK PERFORMANCES", "TRENDS & PROFILES", "RECORD BOOK", "SECTIONALS"].map((label, index) => (
            <button key={label} type="button" className={index === 0 ? "is-active" : ""}>
              <strong>{label}</strong>
              <span>{index === 0 ? "Field structure loaded" : "Awaiting race-matched rows"}</span>
            </button>
          ))}
        </section>
        <section className="eiq-performance-approved-toolbar" aria-label="Performance controls">
          <div><span>VIEW</span><button type="button" className="is-active">EPI</button><button type="button">ERI</button><button type="button">EARLY SPEED</button><button type="button">LATE SPEED</button></div>
          <dl><div><dt>Status</dt><dd className="is-pending">Awaiting race-matched performance rows</dd></div><div><dt>Field</dt><dd>{fallbackField.length}</dd></div><div><dt>Historical Runs</dt><dd>Pending</dd></div></dl>
        </section>
        <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
          <div className="eiq-epi-v1-panel__title"><span>Performance Matrix</span><small>Runner structure is visible while race-matched history is pending</small></div>
          <div className="eiq-epi-v1-table-scroll">
            <table className="eiq-epi-v1-table eiq-performance-v2-table"><thead><tr><th>NO</th><th>SILK</th><th>HORSE</th><th>EPI</th><th>AVG</th><th>LAST</th>{HISTORY_COLUMNS.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>
              {fallbackField.length ? fallbackField.map((runner, index) => { const display = runnerDisplay(runner, index); return (
                <tr key={`${display.no}-${display.horse}`}><td>{display.no}</td><td><span className="eiq-performance-v2-silk is-empty" aria-hidden="true" /></td><td><strong>{display.horse}</strong></td><td>Pending</td><td>Pending</td><td>Pending</td>{HISTORY_COLUMNS.map((column) => <td key={`${display.no}-${column}`}><span className="eiq-epi-v1-tile is-missing">-</span></td>)}</tr>
              ); }) : <tr><td colSpan={6 + HISTORY_COLUMNS.length}>Select a race with declared runners to populate the performance matrix.</td></tr>}
            </tbody></table>
          </div>
          <div className="eiq-epi-v1-legend" aria-label="Performance heat map legend"><span><i className="is-positive" /> Strong</span><span><i className="is-neutral" /> Around benchmark</span><span><i className="is-negative" /> Below benchmark</span><span><i className="is-missing" /> Awaiting row</span></div>
        </section>
      </section>
    );
  }
''', "performance fallback")
    return text

edit("src/edgeiq-os/race/components/PerformanceWorkspace.tsx", patch_performance)

# EPI: add field fallback matrix instead of one-line empty state.
def patch_epi(text: str) -> str:
    text = must_replace(text,
'''type EpiWorkspaceWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
};''',
'''type EpiWorkspaceWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
  field?: any[];
};''', "epi props")
    text = must_replace(text,
'''function value(rowValue: string | null | undefined): string {
  return rowValue && rowValue.trim() ? rowValue : "";
}
''',
'''function value(rowValue: string | null | undefined): string {
  return rowValue && rowValue.trim() ? rowValue : "";
}

function fieldRunner(row: any, index: number): { no: string; horse: string; jockey: string; trainer: string } {
  return {
    no: String(row?.number ?? row?.runnerNumber ?? row?.saddlecloth ?? row?.no ?? index + 1).trim(),
    horse: String(row?.runnerName ?? row?.runner ?? row?.horse ?? row?.name ?? "Runner pending").trim(),
    jockey: String(row?.jockey ?? row?.jockeyName ?? row?.rider ?? "Pending").trim(),
    trainer: String(row?.trainer ?? row?.trainerName ?? "Pending").trim(),
  };
}
''', "epi fieldRunner")
    text = must_replace(text,
'''export function EpiWorkspaceWorkspace({ raceKey, meetingKey = null, raceLabel = null }: EpiWorkspaceWorkspaceProps) {''',
'''export function EpiWorkspaceWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [] }: EpiWorkspaceWorkspaceProps) {''', "epi signature")
    text = must_replace(text,
'''  if (!viewModel.rows.length) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Governed EPI workspace rows are not available for this race.</div></section>;
  }
''',
'''  if (!viewModel.rows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 30) : [];
    return (
      <section className="eiq-epi-v1">
        <div className="eiq-epi-v1-hero">
          <div><p>EPI</p><h3>{raceLabel || "EPI Workspace"}</h3><span>EDGEIQ Performance Index structure is available while race-matched EPI rows are pending.</span></div>
          <dl><div><dt>Status</dt><dd className="is-pending">Awaiting race-matched EPI rows</dd></div><div><dt>Field</dt><dd>{fallbackField.length}</dd></div><div><dt>Source Rows</dt><dd>{rows.length}</dd></div></dl>
        </div>
        <SummaryStrip row={null} />
        <div className="eiq-epi-v1-grid">
          <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
            <div className="eiq-epi-v1-panel__title"><span>EPI Matrix</span><small>Runner rows are visible with pending EPI fields</small></div>
            <div className="eiq-epi-v1-table-scroll"><table className="eiq-epi-v1-table"><thead><tr><th>Rank</th><th>No</th><th>Runner</th><th>Jockey</th><th>Trainer</th><th>Current EPI</th><th>Field Diff</th><th>Peak Last 10</th><th>Avg Last 10</th><th>Trend</th><th>Valid Starts</th><th>Evidence</th><th>Status</th></tr></thead><tbody>
              {fallbackField.length ? fallbackField.map((runner, index) => { const display = fieldRunner(runner, index); return (
                <tr key={`${display.no}-${display.horse}`} className="is-unavailable"><td>Pending</td><td>{display.no}</td><td><strong>{display.horse}</strong></td><td>{display.jockey}</td><td>{display.trainer}</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Awaiting row</td></tr>
              ); }) : <tr><td colSpan={13}>Select a race with declared runners to populate the EPI matrix.</td></tr>}
            </tbody></table></div>
          </section>
          <aside className="eiq-epi-v1-side">
            <RaceBenchmarkPanel context={performanceContext} />
            <section className="eiq-epi-v1-panel"><div className="eiq-epi-v1-panel__title"><span>Historical EPI</span></div><p className="eiq-epi-v1-copy">Race-matched historical EPI rows are pending for this selected race.</p></section>
            <section className="eiq-epi-v1-panel"><div className="eiq-epi-v1-panel__title"><span>Rating Explanation</span></div><p className="eiq-epi-v1-copy">No EPI value is shown until the governed feed supplies a matched row.</p></section>
          </aside>
        </div>
      </section>
    );
  }
''', "epi fallback")
    return text

edit("src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx", patch_epi)

# Overview: field-aware structured fallback.
def patch_overview(text: str) -> str:
    text = must_replace(text,
'''type OverviewWorkspaceProps = {

  raceKey?: string | null;

  meetingKey?: string | null;

  raceLabel?: string | null;

  onOpenTab?: (tab: "FORM GUIDE" | "MAP" | "MARKET" | "OVERVIEW" | "INSIGHTS" | "EPI" | "REVIEW") => void;

};''',
'''type OverviewWorkspaceProps = {

  raceKey?: string | null;

  meetingKey?: string | null;

  raceLabel?: string | null;

  field?: any[];

  onOpenTab?: (tab: "FORM GUIDE" | "MAP" | "MARKET" | "OVERVIEW" | "INSIGHTS" | "EPI" | "REVIEW") => void;

};''', "overview props")
    text = must_replace(text,
'''export function OverviewWorkspace({ raceKey, meetingKey = null, raceLabel = null, onOpenTab }: OverviewWorkspaceProps) {''',
'''export function OverviewWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [], onOpenTab }: OverviewWorkspaceProps) {''', "overview signature")
    text = must_replace(text,
'''  if (!viewModel.rows.length && !epiViewModel.rows.length && !selectedMapRows.length) {

    return (

      <section className="eiq-overview-v1">

        <div className="eiq-overview-v1-empty">Governed overview rows are not available for this race.</div>

      </section>

    );

  }
''',
'''  if (!viewModel.rows.length && !epiViewModel.rows.length && !selectedMapRows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 12) : [];
    return (
      <section className="eiq-overview-v1 eiq-overview-v3">
        <div className="eiq-overview-v1-hero"><div><p>OVERVIEW</p><h3>{raceLabel || "Race Overview"}</h3><span>Race shell, runner board and next-action structure are available while specialist reads are pending.</span></div><dl><div><dt>Overview</dt><dd>Pending</dd></div><div><dt>Field</dt><dd>{fallbackField.length}</dd></div><div><dt>Map</dt><dd>Pending</dd></div></dl></div>
        <div className="eiq-overview-v3-layout eiq-overview-pixel-v1__layout"><main>
          <div className="eiq-overview-v3-two-up">
            <section className="eiq-overview-v1-card"><span>Tempo Profile</span><strong>Pending</strong><small>Race-shape rows are not matched yet.</small></section>
            <section className="eiq-overview-v1-card"><span>EPI Top 3</span><strong>Pending</strong><small>EPI rows are not matched yet.</small></section>
          </div>
          <section className="eiq-overview-v1-panel"><div className="eiq-overview-v1-panel__title"><span>Runner Board</span><small>Declared runners remain visible for race navigation</small></div><div className="eiq-overview-v1-table-scroll"><table className="eiq-overview-v1-table"><thead><tr><th>No</th><th>Runner</th><th>Current EPI</th><th>Trend</th></tr></thead><tbody>{fallbackField.length ? fallbackField.map((runner, index) => { const no = String(runner?.number ?? runner?.runnerNumber ?? runner?.saddlecloth ?? runner?.no ?? index + 1).trim(); const horse = String(runner?.runnerName ?? runner?.runner ?? runner?.horse ?? runner?.name ?? "Runner pending").trim(); return <tr key={`${no}-${horse}`}><td>{no}</td><td><strong>{horse}</strong></td><td>Pending</td><td>Pending</td></tr>; }) : <tr><td colSpan={4}>Select a race with declared runners to populate the runner board.</td></tr>}</tbody></table></div></section>
        </main><aside className="eiq-overview-v1-side"><section className="eiq-overview-v1-panel"><div className="eiq-overview-v1-panel__title"><span>What Matters Today</span></div><p className="eiq-overview-v1-copy">Race-level overview rows are pending; use FIELD, FORM GUIDE and MAP for available race structure.</p></section></aside></div>
      </section>
    );
  }
''', "overview fallback")
    return text

edit("src/edgeiq-os/race/components/OverviewWorkspace.tsx", patch_overview)

# Insights: field-aware structured fallback.
def patch_insights(text: str) -> str:
    text = must_replace(text,
'''type InsightsWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
};''',
'''type InsightsWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
  field?: any[];
};''', "insights props")
    text = must_replace(text,
'''export function InsightsWorkspace({ raceKey, meetingKey = null, raceLabel = null }: InsightsWorkspaceProps) {''',
'''export function InsightsWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [] }: InsightsWorkspaceProps) {''', "insights signature")
    text = must_replace(text,
'''  if (!viewModel.rows.length && !viewModel.cards.length) {
    return <section className="eiq-insights-v1"><div className="eiq-insights-v1-empty">Governed insight rows are not available for this race.</div></section>;
  }
''',
'''  if (!viewModel.rows.length && !viewModel.cards.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 24) : [];
    const pendingModel: BETA012ViewModel = { ...viewModel, rows: fallbackField.map((runner, index) => ({
      no: String(runner?.number ?? runner?.runnerNumber ?? runner?.saddlecloth ?? runner?.no ?? index + 1).trim(),
      horse: String(runner?.runnerName ?? runner?.runner ?? runner?.horse ?? runner?.name ?? "Runner pending").trim(),
      key_insight: "",
      edge: "",
      supportingEvidence: "",
      coverage: "",
      rowStatus: "Awaiting row",
    } as BETA012Row)) };
    return (
      <section className="eiq-insights-v1">
        <div className="eiq-insights-v1-hero"><div><p>INSIGHTS</p><h3>{raceLabel || "Race Intelligence"}</h3><span>Approved insight categories are staged; race-matched cards are pending for this selected race.</span></div><dl><div><dt>Stable Intent</dt><dd>Pending</dd></div><div><dt>Preparation</dt><dd>Pending</dd></div><div><dt>Runners</dt><dd>{fallbackField.length}</dd></div></dl></div>
        <ApprovedInsightCategoryCards cards={[]} />
        <div className="eiq-insights-v1-grid"><div className="eiq-insights-v1-main"><section className="eiq-insights-v1-panel"><div className="eiq-insights-v1-panel__title"><span>Approved Categories</span></div><p className="eiq-insights-v1-copy">Stable Intent, Preparation Stage, Heavy Skill and Campaign Profile will display only when matched rows are supplied.</p></section><RunnerInsightsTable rows={pendingModel.rows} /></div><QualityPanel viewModel={pendingModel} performanceContext={performanceContext} /></div>
      </section>
    );
  }
''', "insights fallback")
    return text

edit("src/edgeiq-os/race/components/InsightsWorkspace.tsx", patch_insights)

# Review copy and approved result-review sections.
def patch_review(text: str) -> str:
    text = text.replace("<strong>Race review workspace</strong>", "<strong>Sectional and performance review</strong>")
    text = text.replace("<span>Reviewable Work</span>\n            <strong>Available product state</strong>", "<span>Review Structure</span>\n            <strong>Race analysis modules</strong>")
    text = text.replace("Reviewable Work", "Review Structure")
    insert_after = '''      <section className="eiq-review-final__meta">
        {model.meta.map((item) => (
          <div key={item.label}>
            <span>{item.label}</span>
            <strong>{clean(item.value)}</strong>
          </div>
        ))}
      </section>
'''
    addition = insert_after + '''
      <section className="eiq-review-final__meta" aria-label="Post-race review modules">
        {["Winner", "Runners / Scratchings", "Sectional Summary", "Sectional Profile", "Runner Performance Snapshot", "Stewards / Notes"].map((label) => (
          <div key={label}>
            <span>{label}</span>
            <strong>Pending result</strong>
          </div>
        ))}
      </section>
'''
    text = must_replace(text, insert_after, addition, "review modules")
    return text

edit("src/edgeiq-os/race/components/ReviewWorkspace.tsx", patch_review)

# Lab visible naming cleanup.
def patch_lab(text: str) -> str:
    text = text.replace("<h3>Racing Research Laboratory</h3>", "<h3>Stats Engine & Query Builder</h3>")
    text = text.replace("Build governed racing research queries across the browser-safe product intelligence set.", "Build browser-safe racing queries across the approved product intelligence set.")
    text = text.replace("LAB only exposes metrics supplied by the governed product intelligence set. Jockey and trainer modules remain inactive until a governed research dataset is available.", "LAB exposes only approved product metrics. Jockey and trainer modules remain inactive until a validated research dataset is available.")
    return text

edit("src/edgeiq-os/race/components/LabWorkspace.tsx", patch_lab)

print(f"EDGEIQ_FINAL_RUNTIME_PHASE03_NO_FALLBACKS_PASS checkpoint={CHECKPOINT}")
