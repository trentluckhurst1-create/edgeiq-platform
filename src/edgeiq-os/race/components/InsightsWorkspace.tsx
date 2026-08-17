import { useEffect, useMemo, useState } from "react";
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
import {
  EiqBadge,
  EiqCard,
  EiqDataTable,
  EiqEmptyState,
  EiqMetric,
  EiqPanel,
  EiqSectionHeader,
  EiqSidePanel,
  EiqStatusBadge,
} from "../../design-system/v1";

type InsightsWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
  field?: any[];
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

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && text.toLowerCase() !== "null" && text.toLowerCase() !== "undefined") return text;
  }
  return "";
}

function displayValue(rowValue: string | null | undefined, fallback = "Not supplied"): string {
  const text = value(rowValue);
  return text || fallback;
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
    <div className="eiq-insights-v2-cards" aria-label="Approved insight categories">
      {ApprovedInsightCategories.map((category) => {
        const card = getCategoryCard(cards, category);
        const hasEvidence = hasCardEvidence(card);
        return (
          <EiqCard density="compact" className="eiq-insights-v2-card" key={category.label}>
            <EiqMetric
              label={category.label}
              value={hasEvidence ? displayValue(card.value) : "Not supplied"}
              detail={hasEvidence
                ? displayValue(card.detail)
                : "Governed feed has not supplied this category for the selected race."}
            />
          </EiqCard>
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
    <section className="eiq-v1-side-panel-section">
      <EiqSectionHeader title="Data Gaps" />
      <dl className="eiq-v1-side-facts">
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
    <EiqPanel className="eiq-v1-standard-table-panel">
      <EiqSectionHeader eyebrow="Runner Insights" title="No, runner, insight, edge, evidence and status" />
      <EiqDataTable
        density="compact"
        className="eiq-insights-v2-table"
        wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
      >
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
                  <td><EiqStatusBadge status={rowStatusLabel(row.rowStatus)} /></td>
                </tr>
              );
            })}
          </tbody>
      </EiqDataTable>
    </EiqPanel>
  );
}

function GovernedEvidenceList({ rows }: { rows: BETA012Row[] }) {
  const topRows = rows.filter((row) => value(row.key_insight) || value(row.edge) || value(row.supportingEvidence)).slice(0, 5);
  return (
    <EiqPanel className="eiq-insights-v2-panel">
      <EiqSectionHeader title="Governed Evidence" />
      <ol className="eiq-insights-v1-list eiq-v1-standard-list">
        {topRows.length ? topRows.map((row) => (
          <li key={`top-${value(row.no)}-${value(row.horse)}`}>
            <strong>{displayValue(row.horse)}</strong>
            <span>{displayValue(row.key_insight || row.supportingEvidence || row.edge)}</span>
          </li>
        )) : <li><span>Runner-level evidence has not been supplied for this race.</span></li>}
      </ol>
    </EiqPanel>
  );
}

function CertifiedEvidencePanel({ context }: { context: PerformanceIntelligenceRaceContext | null }) {
  const race = context?.race ?? null;
  return (
    <section className="eiq-v1-side-panel-section">
      <EiqSectionHeader title="Certified Evidence" />
      {race ? (
        <dl className="eiq-v1-side-facts">
          <div><dt>Benchmark</dt><dd>{formatBenchmarkLevel(race.selected_benchmark_level)}</dd></div>
          <div><dt>Profiles</dt><dd>{context?.horses.length ?? 0}</dd></div>
          <div><dt>History</dt><dd>{context?.historical.length ?? 0}</dd></div>
        </dl>
      ) : (
        <p className="eiq-v1-analytical-copy">Certified performance evidence is not available for this race.</p>
      )}
    </section>
  );
}

function QualityPanel({ viewModel, performanceContext }: { viewModel: BETA012ViewModel; performanceContext: PerformanceIntelligenceRaceContext | null }) {
  return (
    <EiqSidePanel className="eiq-v1-analytical-side-panel">
      <CertifiedEvidencePanel context={performanceContext} />
      <DataGaps viewModel={viewModel} />
      <section className="eiq-v1-side-panel-section">
        <EiqSectionHeader title="Workspace Status" />
        <dl className="eiq-v1-side-facts">
          <div><dt>Status</dt><dd><EiqStatusBadge status={viewModel.status} /></dd></div>
          <div><dt>Matched Rows</dt><dd>{viewModel.source.matchedRows}</dd></div>
          <div><dt>Loaded Rows</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </section>
    </EiqSidePanel>
  );
}

export function InsightsWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [] }: InsightsWorkspaceProps) {
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
    return <section className="eiq-insights-v2-workspace eiq-v1-standard-workspace"><EiqEmptyState title="Loading governed insights." /></section>;
  }

  if (error) {
    return <section className="eiq-insights-v2-workspace eiq-v1-standard-workspace"><EiqEmptyState title={error} /></section>;
  }

  if (!viewModel.rows.length && !viewModel.cards.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 24) : [];
    const pendingModel: BETA012ViewModel = { ...viewModel, rows: fallbackField.map((runner, index) => ({
      no: firstText(runner?.official?.number, runner?.number, runner?.runnerNumber, runner?.saddlecloth, runner?.no, index + 1),
      horse: firstText(runner?.official?.runner, runner?.runner, runner?.horse, runner?.runnerName, runner?.name, "Runner pending"),
      key_insight: "",
      edge: "",
      supportingEvidence: "",
      coverage: "",
      rowStatus: "Awaiting row",
    } as BETA012Row)) };
    return (
      <section className="eiq-insights-v2-workspace eiq-v1-standard-workspace">
        <EiqPanel className="eiq-insights-v2-intro"><EiqSectionHeader eyebrow="INSIGHTS" title={raceLabel || "Race Intelligence"} meta={<EiqBadge tone="warning">Pending</EiqBadge>} /><p className="eiq-v1-analytical-copy">Approved insight categories are staged; race-matched cards are pending for this selected race.</p><dl className="eiq-v1-inline-facts"><div><dt>Stable Intent</dt><dd>Pending</dd></div><div><dt>Preparation</dt><dd>Pending</dd></div><div><dt>Runners</dt><dd>{fallbackField.length}</dd></div></dl></EiqPanel>
        <ApprovedInsightCategoryCards cards={[]} />
        <div className="eiq-insights-v1-grid eiq-insights-v2-grid eiq-v1-analytical-grid"><div className="eiq-insights-v1-main"><EiqPanel><EiqSectionHeader title="Approved Categories" /><p className="eiq-v1-analytical-copy">Stable Intent, Preparation Stage, Heavy Skill and Campaign Profile will display only when matched rows are supplied.</p></EiqPanel><RunnerInsightsTable rows={pendingModel.rows} /></div><QualityPanel viewModel={pendingModel} performanceContext={performanceContext} /></div>
      </section>
    );
  }

  return (
    <section className="eiq-insights-v2-workspace eiq-v1-standard-workspace">
      <EiqPanel className="eiq-insights-v2-intro">
        <EiqSectionHeader
          eyebrow="INSIGHTS"
          title={raceLabel || "Governed Race Intelligence"}
          meta={<EiqBadge tone="info">Governed categories</EiqBadge>}
        />
        <p className="eiq-v1-analytical-copy">Governed categories only. Unsupported reads remain unavailable.</p>
        <dl className="eiq-v1-inline-facts">
          <div><dt>Workspace</dt><dd>{viewModel.workspaceId}</dd></div>
          <div><dt>Status</dt><dd>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
        </dl>
      </EiqPanel>
      <ApprovedInsightCategoryCards cards={viewModel.cards} />
      <div className="eiq-insights-v1-grid eiq-insights-v2-grid eiq-v1-analytical-grid">
        <div className="eiq-insights-v1-main">
          <EiqPanel>
            <EiqSectionHeader title="Approved Categories" />
            <p className="eiq-v1-analytical-copy">
              Stable Intent, Preparation Stage, Heavy Skill and Campaign Profile are shown only when supplied by governed sources.
            </p>
          </EiqPanel>
          <GovernedEvidenceList rows={viewModel.rows} />
          <RunnerInsightsTable rows={viewModel.rows} />
        </div>
        <QualityPanel viewModel={viewModel} performanceContext={performanceContext} />
      </div>
    </section>
  );
}
