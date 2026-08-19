from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "InsightsWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_INSIGHTS_TRACE_V1.md"


COMPONENT_SOURCE = r'''import { useEffect, useMemo, useState } from "react";
import {
  buildInsightsViewModel,
  loadInsightsTerminalFeed,
  type BETA012Card,
  type BETA012Row,
  type BETA012ViewModel,
} from "../services/insightsFeed";
import {
  buildPerformanceIntelligenceService,
  formatBenchmarkLevel,
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceRaceContext,
} from "../../services/performance-intelligence";

type InsightsWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
};

type ApprovedInsightCategory = {
  label: string;
  aliases: string[];
};

const ApprovedInsightCategories: ApprovedInsightCategory[] = [
  { label: "Stable Intent", aliases: ["stable intent", "stable"] },
  { label: "Preparation Stage", aliases: ["preparation stage", "preparation", "prep"] },
  { label: "Heavy Skill", aliases: ["heavy skill", "heavy"] },
  { label: "Campaign Profile", aliases: ["campaign profile", "campaign"] },
];

function value(rowValue: string | null | undefined): string {
  return rowValue && rowValue.trim() ? rowValue : "";
}

function displayValue(rowValue: string | null | undefined, fallback = "Not supplied"): string {
  const text = value(rowValue);
  return text || fallback;
}

function statusClass(valueText: string | null): string {
  const text = value(valueText).toLowerCase();
  if (text.includes("pending") || text.includes("unavailable") || !text) return "is-pending";
  return "is-current";
}

function rowStatusLabel(status: string | null): string {
  const text = value(status).replace(/_/g, " ");
  return text || "Not supplied";
}

function hasCardEvidence(card: BETA012Card | null): card is BETA012Card {
  return Boolean(card && (value(card.value) || value(card.detail)));
}

function matchesCategory(card: BETA012Card, category: ApprovedInsightCategory): boolean {
  const text = `${value(card.cardType)} ${value(card.title)}`.toLowerCase();
  return category.aliases.some((alias) => text.includes(alias));
}

function getCategoryCard(cards: BETA012Card[], category: ApprovedInsightCategory): BETA012Card | null {
  return cards.find((card) => matchesCategory(card, category)) ?? null;
}

function ApprovedInsightCategoryCards({ cards }: { cards: BETA012Card[] }) {
  return (
    <div className="eiq-insights-v1-cards" aria-label="Approved insight categories">
      {ApprovedInsightCategories.map((category) => {
        const card = getCategoryCard(cards, category);
        const hasEvidence = hasCardEvidence(card);
        return (
          <section className="eiq-insights-v1-card" key={category.label}>
            <span>{category.label}</span>
            <strong>{hasEvidence ? displayValue(card.value) : "Not supplied"}</strong>
            <p>
              {hasEvidence
                ? displayValue(card.detail)
                : "Governed feed has not supplied this category for the selected race."}
            </p>
          </section>
        );
      })}
    </div>
  );
}

function DataGaps({ viewModel }: { viewModel: BETA012ViewModel }) {
  const approvedSupplied = ApprovedInsightCategories.filter((category) => {
    const card = getCategoryCard(viewModel.cards, category);
    return hasCardEvidence(card);
  }).length;
  const runnersWithInsight = viewModel.rows.filter((row) => value(row.key_insight) || value(row.edge)).length;
  const pendingRunners = Math.max(0, viewModel.rows.length - runnersWithInsight);
  const otherGovernedCards = viewModel.cards.filter((card) => {
    if (!hasCardEvidence(card)) return false;
    return !ApprovedInsightCategories.some((category) => matchesCategory(card, category));
  }).length;

  return (
    <section className="eiq-insights-v1-panel">
      <div className="eiq-insights-v1-panel__title"><span>Data Gaps</span></div>
      <dl className="eiq-insights-v1-facts">
        <div><dt>Approved Categories</dt><dd>{approvedSupplied} / {ApprovedInsightCategories.length}</dd></div>
        <div><dt>Runner Reads</dt><dd>{runnersWithInsight} / {viewModel.rows.length}</dd></div>
        <div><dt>Pending Runners</dt><dd>{pendingRunners}</dd></div>
        <div><dt>Other Governed Signals</dt><dd>{otherGovernedCards}</dd></div>
      </dl>
    </section>
  );
}

function RunnerInsightsTable({ rows }: { rows: BETA012Row[] }) {
  return (
    <section className="eiq-insights-v1-panel eiq-insights-v1-table-panel">
      <div className="eiq-insights-v1-panel__title">
        <span>Runner Insights</span>
        <small>No | Runner | Insight | Edge | Evidence | Status</small>
      </div>
      <div className="eiq-insights-v1-table-scroll">
        <table className="eiq-insights-v1-table">
          <thead>
            <tr>
              <th>No</th>
              <th>Runner</th>
              <th>Insight</th>
              <th>Edge</th>
              <th>Evidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const insight = value(row.key_insight);
              const edge = value(row.edge);
              const evidence = value(row.supportingEvidence) || value(row.coverage);
              const pending = !insight && !edge && !evidence;
              return (
                <tr key={`${value(row.no)}-${value(row.horse)}`} className={pending ? "is-pending" : ""}>
                  <td>{displayValue(row.no, "")}</td>
                  <td><strong>{displayValue(row.horse)}</strong></td>
                  <td>{insight || "Awaiting governed insight"}</td>
                  <td>{edge || "Not supplied"}</td>
                  <td>{evidence || "Not supplied"}</td>
                  <td>{rowStatusLabel(row.rowStatus)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function GovernedEvidenceList({ rows }: { rows: BETA012Row[] }) {
  const topRows = rows.filter((row) => value(row.key_insight) || value(row.edge) || value(row.supportingEvidence)).slice(0, 5);
  return (
    <section className="eiq-insights-v1-panel">
      <div className="eiq-insights-v1-panel__title"><span>Governed Evidence</span></div>
      <ol className="eiq-insights-v1-list">
        {topRows.length ? topRows.map((row) => (
          <li key={`top-${value(row.no)}-${value(row.horse)}`}>
            <strong>{displayValue(row.horse)}</strong>
            <span>{displayValue(row.key_insight || row.supportingEvidence || row.edge)}</span>
          </li>
        )) : <li><span>Runner-level evidence has not been supplied for this race.</span></li>}
      </ol>
    </section>
  );
}

function CertifiedEvidencePanel({ context }: { context: PerformanceIntelligenceRaceContext | null }) {
  const race = context?.race ?? null;
  return (
    <section className="eiq-insights-v1-panel">
      <div className="eiq-insights-v1-panel__title"><span>Certified Evidence</span></div>
      {race ? (
        <dl className="eiq-insights-v1-facts">
          <div><dt>Benchmark</dt><dd>{formatBenchmarkLevel(race.selected_benchmark_level)}</dd></div>
          <div><dt>Profiles</dt><dd>{context?.horses.length ?? 0}</dd></div>
          <div><dt>History</dt><dd>{context?.historical.length ?? 0}</dd></div>
        </dl>
      ) : (
        <p className="eiq-insights-v1-copy">Certified performance evidence is not available for this race.</p>
      )}
    </section>
  );
}

function QualityPanel({ viewModel, performanceContext }: { viewModel: BETA012ViewModel; performanceContext: PerformanceIntelligenceRaceContext | null }) {
  return (
    <aside className="eiq-insights-v1-side">
      <CertifiedEvidencePanel context={performanceContext} />
      <DataGaps viewModel={viewModel} />
      <section className="eiq-insights-v1-panel">
        <div className="eiq-insights-v1-panel__title"><span>Workspace Status</span></div>
        <dl className="eiq-insights-v1-facts">
          <div><dt>Status</dt><dd className={statusClass(viewModel.status)}>{viewModel.status}</dd></div>
          <div><dt>Matched Rows</dt><dd>{viewModel.source.matchedRows}</dd></div>
          <div><dt>Loaded Rows</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </section>
    </aside>
  );
}

export function InsightsWorkspace({ raceKey, meetingKey = null, raceLabel = null }: InsightsWorkspaceProps) {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof loadInsightsTerminalFeed>>>([]);
  const [performanceContext, setPerformanceContext] = useState<PerformanceIntelligenceRaceContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadInsightsTerminalFeed()
      .then((feedRows) => {
        if (!cancelled) {
          setRows(feedRows);
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setRows([]);
          setError(loadError instanceof Error ? loadError.message : "Insights feed failed");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadPerformanceIntelligenceFeed()
      .then((feed) => {
        if (!cancelled) setPerformanceContext(buildPerformanceIntelligenceService(feed).getRaceContext(raceKey));
      })
      .catch((loadError) => {
        console.warn("Certified performance intelligence feed unavailable", loadError);
        if (!cancelled) setPerformanceContext(null);
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey]);

  const viewModel = useMemo(() => buildInsightsViewModel(raceKey, rows, meetingKey), [raceKey, rows, meetingKey]);

  if (loading) {
    return <section className="eiq-insights-v1"><div className="eiq-insights-v1-empty">Loading governed insights.</div></section>;
  }

  if (error) {
    return <section className="eiq-insights-v1"><div className="eiq-insights-v1-empty">{error}</div></section>;
  }

  if (!viewModel.rows.length && !viewModel.cards.length) {
    return <section className="eiq-insights-v1"><div className="eiq-insights-v1-empty">Governed insight rows are not available for this race.</div></section>;
  }

  return (
    <section className="eiq-insights-v1">
      <div className="eiq-insights-v1-hero">
        <div>
          <p>INSIGHTS</p>
          <h3>{raceLabel || "Governed Race Intelligence"}</h3>
          <span>Governed categories only. Unsupported reads remain unavailable.</span>
        </div>
        <dl>
          <div><dt>Workspace</dt><dd>{viewModel.workspaceId}</dd></div>
          <div><dt>Status</dt><dd className={statusClass(viewModel.status)}>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
        </dl>
      </div>
      <ApprovedInsightCategoryCards cards={viewModel.cards} />
      <div className="eiq-insights-v1-grid">
        <div className="eiq-insights-v1-main">
          <section className="eiq-insights-v1-panel">
            <div className="eiq-insights-v1-panel__title"><span>Approved Categories</span></div>
            <p className="eiq-insights-v1-copy">
              Stable Intent, Preparation Stage, Heavy Skill and Campaign Profile are shown only when supplied by governed sources.
            </p>
          </section>
          <GovernedEvidenceList rows={viewModel.rows} />
          <RunnerInsightsTable rows={viewModel.rows} />
        </div>
        <QualityPanel viewModel={viewModel} performanceContext={performanceContext} />
      </div>
    </section>
  );
}
'''


CSS_APPEND = r'''

/* EDGEIQ INSIGHTS FINAL SPEC V1 */
.eiq-insights-v1 .eiq-insights-v1-card {
  min-height: 118px;
}

.eiq-insights-v1 .eiq-insights-v1-card p {
  min-height: 0;
}

.eiq-insights-v1 .eiq-insights-v1-table {
  min-width: 1040px;
}

.eiq-insights-v1 .eiq-insights-v1-table th:nth-child(5),
.eiq-insights-v1 .eiq-insights-v1-table td:nth-child(5),
.eiq-insights-v1 .eiq-insights-v1-table th:nth-child(6),
.eiq-insights-v1 .eiq-insights-v1-table td:nth-child(6) {
  text-align: left;
}

.eiq-insights-v1 .eiq-insights-v1-table td:nth-child(5) {
  max-width: 360px;
}
'''


TRACE_TEXT = """# EDGEiQ Insights Trace V1

Workspace: INSIGHTS

Purpose: governed intelligence display only.

Approved categories:
- Stable Intent
- Preparation Stage
- Heavy Skill
- Campaign Profile

Canonical feed:
- public/data/edgeiq_insights_terminal_feed_v1.csv

Performance evidence support:
- public/performance-intelligence/performance_intelligence_current_race_v1.csv through loadPerformanceIntelligenceFeed

Rules applied:
- No product-facing certainty label.
- No tips or wagering calls.
- No generic AI analysis generated in React.
- Unsupported categories show restrained unavailable states.
- Runner table displays only governed insight, edge, evidence and status fields.
"""


def main() -> None:
    COMPONENT.write_text(COMPONENT_SOURCE, encoding="utf-8")
    css_text = CSS.read_text(encoding="utf-8")
    if "/* EDGEIQ INSIGHTS FINAL SPEC V1 */" not in css_text:
        CSS.write_text(css_text.rstrip() + "\n" + CSS_APPEND.lstrip(), encoding="utf-8")
    TRACE.parent.mkdir(parents=True, exist_ok=True)
    TRACE.write_text(TRACE_TEXT, encoding="utf-8")
    print("EDGEIQ_INSIGHTS_FINAL_SPEC_APPLIED")


if __name__ == "__main__":
    main()
