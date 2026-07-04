import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import EcologyResearchPanel from "./EcologyResearchPanel";
import RacingFeedHealthPanel from "./RacingFeedHealthPanel";

type CsvRow = Record<string, string>;
type Tone = "good" | "warn" | "bad" | "neutral";

const FILES = {
  accountability: "/data/edgeiq_execution_accountability.csv",
  truthLoop: "/data/edgeiq_results_truth_loop.csv",
  clv: "/data/edgeiq_clv_memory.csv",
  tape: "/data/edgeiq_market_tape_summary.csv",
  execution: "/data/edgeiq_execution_engine_v4.csv",
  health: "/data/edgeiq_pipeline_health.csv",
  sectionalCatalogue: "/data/edgeiq_racingcom_sectional_catalogue.csv",
  sectionalSchema: "/data/edgeiq_sectional_schema_v2.csv",
  sectionalInventory: "/data/edgeiq_sectional_scraper_inventory.csv",
  sectionalValidation: "/data/edgeiq_sectional_validation_engine.csv",
  sectionalValidationSummary: "/data/edgeiq_sectional_validation_summary.csv",
  sectionalIdentitySummary: "/data/edgeiq_sectional_identity_summary_v1.csv",
  trustedSectionalsSummary: "/data/edgeiq_trusted_sectional_universe_summary.csv",
  sectionalMasterSummary: "/data/edgeiq_sectional_master_summary_v1.csv",
  sectionalHealthSummary: "/data/edgeiq_sectional_health_summary.csv",
  payloadReconstructionSummary: "/data/edgeiq_sectional_payload_reconstruction_summary_v1.csv",
  physicsSummary: "/data/edgeiq_sectional_physics_summary_v1.csv",
  canonicalSplits: "/data/edgeiq_canonical_split_schema_v1.csv",
  horseAliases: "/data/edgeiq_horse_alias_engine_v1.csv",
  trackAliases: "/data/edgeiq_track_alias_engine_v1.csv",
  fieldCompositionSummary: "/data/edgeiq_sectional_field_composition_summary_v1.csv",
  identityV2Summary: "/data/edgeiq_sectional_identity_summary_v2.csv",
  identityV3Summary: "/data/edgeiq_sectional_identity_summary_v3.csv",
  runnerGraphSummary: "/data/edgeiq_runner_entity_graph_summary_v1.csv",
  runnerConflicts: "/data/edgeiq_runner_conflict_resolution_v1.csv",
  researchDashboardFeed: "/data/edgeiq_research_dashboard_feed_v1.csv",
  researchDashboardSummary: "/data/edgeiq_research_dashboard_summary_v1.csv",
  researchDashboardTopPriorities: "/data/edgeiq_research_dashboard_top_priorities_v1.csv",
  researchDashboardWatchlist: "/data/edgeiq_research_dashboard_watchlist_v1.csv",
};

function clean(value: unknown): string {
  const out = String(value ?? "").trim();
  return out && !["-", "NAN", "NULL", "UNDEFINED"].includes(out.toUpperCase()) ? out : "";
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function num(value: unknown): number {
  const parsed = Number(clean(value).replace(/[$,%]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function display(value: unknown, fallback = "Not available"): string {
  return clean(value) || fallback;
}

function metric(rows: CsvRow[], key: string): string {
  return clean(rows.find((row) => clean(row.metric) === key)?.value);
}

function summaryValue(rows: CsvRow[], key: string, fallback = "0"): string {
  return display(metric(rows, key), fallback);
}

function groupCount(rows: CsvRow[], key: string): Array<[string, number]> {
  const counts = new Map<string, number>();
  rows.forEach((row) => {
    const value = clean(row[key]) || "UNKNOWN";
    counts.set(value, (counts.get(value) ?? 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function panelRows(rows: CsvRow[], panel: string, limit = 8): CsvRow[] {
  return rows
    .filter((row) => upper(row.panel) === panel)
    .sort((a, b) => num(a.display_rank) - num(b.display_rank))
    .slice(0, limit);
}

function toneFrom(value: unknown): Tone {
  const v = upper(value);
  if (!v) return "neutral";
  if (
    v.includes("FAIL")
    || v.includes("BROKEN")
    || v.includes("UNSAFE")
    || v.includes("REJECT")
    || v === "F"
  ) {
    return "bad";
  }
  if (
    v.includes("WARN")
    || v.includes("WATCH")
    || v.includes("PARTIAL")
    || v.includes("PENDING")
    || v.includes("WEAK")
    || v.includes("LOW")
    || v.includes("DRIFT")
    || v === "B"
  ) {
    return "warn";
  }
  if (
    v.includes("ALLOW")
    || v.includes("GOOD")
    || v.includes("HEALTHY")
    || v.includes("TRUST")
    || v.includes("STABLE")
    || v === "A"
    || v.includes("OK")
  ) {
    return "good";
  }
  return "neutral";
}

async function readCsv(path: string): Promise<CsvRow[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const csv = await response.text();
    return Papa.parse<CsvRow>(csv, { header: true, skipEmptyLines: true }).data ?? [];
  } catch {
    return [];
  }
}

export default function LearningCentre(): React.ReactElement {
  const [data, setData] = useState<Record<string, CsvRow[]>>({});
  const [loadedAt, setLoadedAt] = useState("");

  useEffect(() => {
    let alive = true;

    async function load(): Promise<void> {
      const entries = await Promise.all(
        Object.entries(FILES).map(async ([key, path]) => [key, await readCsv(path)] as const),
      );
      if (!alive) return;
      setData(Object.fromEntries(entries));
      setLoadedAt(new Date().toLocaleTimeString());
    }

    load();
    const timer = window.setInterval(load, 60000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const accountRows = data.accountability ?? [];
  const truthRows = data.truthLoop ?? [];
  const clvRows = data.clv ?? [];
  const tapeRows = data.tape ?? [];
  const executionRows = data.execution ?? [];
  const healthRows = data.health ?? [];
  const sectionalCatalogueRows = data.sectionalCatalogue ?? [];
  const sectionalSchemaRows = data.sectionalSchema ?? [];
  const sectionalInventoryRows = data.sectionalInventory ?? [];
  const sectionalValidationRows = data.sectionalValidation ?? [];
  const sectionalValidationSummaryRows = data.sectionalValidationSummary ?? [];
  const sectionalIdentitySummaryRows = data.sectionalIdentitySummary ?? [];
  const trustedSectionalsSummaryRows = data.trustedSectionalsSummary ?? [];
  const sectionalMasterSummaryRows = data.sectionalMasterSummary ?? [];
  const sectionalHealthSummaryRows = data.sectionalHealthSummary ?? [];
  const payloadReconstructionSummaryRows = data.payloadReconstructionSummary ?? [];
  const physicsSummaryRows = data.physicsSummary ?? [];
  const canonicalSplitRows = data.canonicalSplits ?? [];
  const horseAliasRows = data.horseAliases ?? [];
  const trackAliasRows = data.trackAliases ?? [];
  const fieldCompositionSummaryRows = data.fieldCompositionSummary ?? [];
  const identityV2SummaryRows = data.identityV2Summary ?? [];
  const identityV3SummaryRows = data.identityV3Summary ?? [];
  const runnerGraphSummaryRows = data.runnerGraphSummary ?? [];
  const runnerConflictRows = data.runnerConflicts ?? [];
  const researchDashboardRows = data.researchDashboardFeed ?? [];
  const researchDashboardSummaryRows = data.researchDashboardSummary ?? [];
  const researchDashboardTopRows = data.researchDashboardTopPriorities ?? [];
  const researchDashboardWatchlistRows = data.researchDashboardWatchlist ?? [];

  const decisionDistribution = useMemo(() => groupCount(executionRows, "execution_decision"), [executionRows]);
  const accountabilityDistribution = useMemo(() => groupCount(accountRows, "accountability_grade"), [accountRows]);
  const movementDistribution = useMemo(() => groupCount(tapeRows, "steam_drift"), [tapeRows]);
  const qualityDistribution = useMemo(() => groupCount(truthRows, "execution_quality"), [truthRows]);
  const healthWarnings = useMemo(() => healthRows.filter((row) => ["WARN", "FAIL"].includes(upper(row.status))).slice(0, 8), [healthRows]);

  const executionSummary = useMemo(() => {
    const rejected = executionRows.filter((row) => ["KILL", "SUPPRESS", "NO_PRICE", "SCRATCHED"].includes(upper(row.execution_decision))).length;
    const execute = executionRows.filter((row) => upper(row.execution_decision) === "EXECUTE").length;
    const pending = truthRows.filter((row) => upper(row.result_status) === "PENDING").length;
    const positiveClv = truthRows.filter((row) => clean(row.clv_result) && num(row.clv_result) >= 0).length;
    const lateMoves = tapeRows.filter((row) => upper(row.late_move_flag) === "YES").length;
    return { rejected, execute, pending, positiveClv, lateMoves };
  }, [executionRows, truthRows, tapeRows]);

  const researchCommand = useMemo(() => ({
    dashboardRows: summaryValue(researchDashboardSummaryRows, "dashboard_rows"),
    topPriorityRows: summaryValue(researchDashboardSummaryRows, "top_priority_rows"),
    watchlistRows: summaryValue(researchDashboardSummaryRows, "watchlist_rows"),
    durableRows: summaryValue(researchDashboardSummaryRows, "durable_structure_rows"),
    strengtheningRows: summaryValue(researchDashboardSummaryRows, "strengthening_structure_rows"),
    activeRows: summaryValue(researchDashboardSummaryRows, "active_research_rows"),
    rejectedRows: summaryValue(researchDashboardSummaryRows, "rejected_noise_rows"),
    liveModelling: summaryValue(researchDashboardSummaryRows, "live_modelling_yes"),
    liveExecution: summaryValue(researchDashboardSummaryRows, "live_execution_yes"),
    commandSummary: panelRows(researchDashboardRows, "COMMAND_SUMMARY", 6),
    durableFeed: panelRows(researchDashboardRows, "DURABLE_STRUCTURE", 6),
    strengtheningFeed: panelRows(researchDashboardRows, "STRENGTHENING_STRUCTURES", 6),
    activeFeed: panelRows(researchDashboardRows, "ACTIVE_RESEARCH", 8),
    rejectedFeed: panelRows(researchDashboardRows, "REJECTED_NOISE", 8),
    validationFeed: panelRows(researchDashboardRows, "VALIDATION_HEALTH", 4),
    longitudinalFeed: panelRows(researchDashboardRows, "LONGITUDINAL_HEALTH", 4),
  }), [researchDashboardRows, researchDashboardSummaryRows]);

  const sectionalSummary = useMemo(() => ({
    catalogueRows: sectionalCatalogueRows.length,
    schemaRows: sectionalSchemaRows.length,
    availableRows: sectionalCatalogueRows.filter((row) => upper(row.sectional_available) === "YES").length,
    inventoryFiles: sectionalInventoryRows.length,
    validationCoverage: summaryValue(sectionalValidationSummaryRows, "coverage_pct", "0.0"),
    matchedRows: summaryValue(sectionalValidationSummaryRows, "matched_rows"),
    missingRows: summaryValue(sectionalValidationSummaryRows, "missing_rows"),
    badRows: summaryValue(sectionalValidationSummaryRows, "bad_rows"),
    trustedRows: summaryValue(sectionalIdentitySummaryRows, "trusted_rows"),
    likelyRows: summaryValue(sectionalIdentitySummaryRows, "likely_rows"),
    unmatchedRows: summaryValue(sectionalIdentitySummaryRows, "unmatched_rows"),
    duplicateConflicts: summaryValue(sectionalIdentitySummaryRows, "duplicate_conflicts"),
    trustedUniverseRows: summaryValue(trustedSectionalsSummaryRows, "trusted_universe_rows"),
    masterRows: summaryValue(sectionalMasterSummaryRows, "canonical_rows"),
    modellingRows: summaryValue(sectionalMasterSummaryRows, "trusted_modelling_rows"),
    reconstructionSuccess: summaryValue(payloadReconstructionSummaryRows, "reconstruction_success_pct", "0.0"),
    reconstructionRecovered: summaryValue(payloadReconstructionSummaryRows, "recovered_payloads"),
    physicsTrusted: summaryValue(physicsSummaryRows, "trusted_physics_rows"),
    physicsBroken: summaryValue(physicsSummaryRows, "broken_ladders"),
    canonicalRows: String(canonicalSplitRows.length),
  }), [
    sectionalCatalogueRows,
    sectionalSchemaRows,
    sectionalInventoryRows,
    sectionalValidationSummaryRows,
    sectionalIdentitySummaryRows,
    trustedSectionalsSummaryRows,
    sectionalMasterSummaryRows,
    payloadReconstructionSummaryRows,
    physicsSummaryRows,
    canonicalSplitRows,
  ]);

  const identitySummary = useMemo(() => ({
    horseAliases: String(horseAliasRows.length),
    trackAliases: String(trackAliasRows.length),
    fieldTrusted: summaryValue(fieldCompositionSummaryRows, "best_trusted"),
    fieldLikely: summaryValue(fieldCompositionSummaryRows, "best_likely"),
    fieldUnmatched: summaryValue(fieldCompositionSummaryRows, "best_unmatched"),
    v2Trusted: summaryValue(identityV2SummaryRows, "trusted_identity_rows"),
    v2Ambiguous: summaryValue(identityV2SummaryRows, "unresolved_ambiguities"),
    runnerTrusted: summaryValue(identityV3SummaryRows, "trusted_runner_identities"),
    runnerExecutionSafe: summaryValue(identityV3SummaryRows, "trusted_execution_rows"),
    graphSuccess: summaryValue(runnerGraphSummaryRows, "graph_match_success_pct", "0.0"),
    conflicts: String(runnerConflictRows.length),
  }), [
    horseAliasRows,
    trackAliasRows,
    fieldCompositionSummaryRows,
    identityV2SummaryRows,
    identityV3SummaryRows,
    runnerGraphSummaryRows,
    runnerConflictRows,
  ]);

  const accountabilityRows = useMemo(
    () => [...accountRows].sort((a, b) => num(b.rows) - num(a.rows)).slice(0, 8),
    [accountRows],
  );
  const clvRowsTop = useMemo(
    () => [...clvRows].filter((row) => clean(row.horse)).slice(0, 8),
    [clvRows],
  );

  return (
    <div className="edgeiq-learning-terminal">
      <div className="edgeiq-learning-hero">
        <div>
          <div className="edgeiq-kicker">LEARNING / RESEARCH</div>
          <h1>Research + Validation Terminal</h1>
          <p>
            Execution truth, market tape memory, sectional integrity and ecology research live together here,
            but only the QLD ecology stack is explicitly locked to offline research.
          </p>
        </div>
        <div className="edgeiq-heartbeat">
          <span className="pulse-dot" />
          RESEARCH REFRESH
          <strong>{loadedAt || "LOADING"}</strong>
        </div>
      </div>

      <div className="edgeiq-terminal-stat-grid">
        <TerminalStat label="Research feed" value={researchCommand.dashboardRows} sub={`${researchCommand.topPriorityRows} top priorities`} tone="good" />
        <TerminalStat label="Watchlist" value={researchCommand.watchlistRows} sub={`${researchCommand.rejectedRows} rejected/noise`} tone={num(researchCommand.watchlistRows) ? "warn" : "neutral"} />
        <TerminalStat label="Boundary lock" value={`${researchCommand.liveModelling}/${researchCommand.liveExecution}`} sub="live_modelling_yes / live_execution_yes" tone={num(researchCommand.liveModelling) || num(researchCommand.liveExecution) ? "bad" : "good"} />
        <TerminalStat label="Sectionals" value={sectionalSummary.availableRows} sub={`${sectionalSummary.catalogueRows} catalogue rows`} tone={sectionalSummary.availableRows ? "good" : "warn"} />
        <TerminalStat label="Trusted universe" value={sectionalSummary.trustedUniverseRows} sub={`${sectionalSummary.trustedRows} trusted`} tone={num(sectionalSummary.trustedRows) ? "good" : "warn"} />
        <TerminalStat label="Physics rows" value={sectionalSummary.physicsTrusted} sub={`${sectionalSummary.canonicalRows} canonical rows`} tone={num(sectionalSummary.physicsTrusted) ? "good" : "warn"} />
        <TerminalStat label="Execution rows" value={executionRows.length} sub={`${executionSummary.execute} execute / ${executionSummary.rejected} rejected`} tone="neutral" />
        <TerminalStat label="Pipeline warnings" value={healthWarnings.length} sub={healthWarnings.length ? "investigate health rows" : "no current warnings"} tone={healthWarnings.length ? "warn" : "good"} />
      </div>

      <RacingFeedHealthPanel />

      <EcologyResearchPanel />

      <div className="edgeiq-learning-grid">
        <section className="edgeiq-panel span-2">
          <div className="edgeiq-panel-title">RESEARCH COMMAND FEED</div>
          <div className="edgeiq-learning-grid">
            <div className="edgeiq-terminal-subgrid">
              <CompactTable
                title="Command summary"
                rows={researchCommand.commandSummary}
                empty="Research command summary has not generated rows yet."
              />
              <CompactTable
                title="Top priorities"
                rows={researchDashboardTopRows}
                empty="No top research priorities available."
              />
            </div>
            <div className="edgeiq-terminal-subgrid">
              <CompactTable
                title="Watchlist"
                rows={researchDashboardWatchlistRows}
                empty="No research watchlist rows available."
              />
              <details className="edgeiq-audit-details">
                <summary>Deep research lanes</summary>
                <div className="edgeiq-audit-details-body edgeiq-terminal-subgrid">
                  <CompactTable title="Durable structure" rows={researchCommand.durableFeed} empty="No durable structure rows." compact />
                  <CompactTable title="Strengthening structures" rows={researchCommand.strengtheningFeed} empty="No strengthening rows." compact />
                  <CompactTable title="Active research" rows={researchCommand.activeFeed} empty="No active research rows." compact />
                  <CompactTable title="Rejected / noise" rows={researchCommand.rejectedFeed} empty="No rejected/noise rows." compact />
                  <CompactTable title="Validation health" rows={[...researchCommand.validationFeed, ...researchCommand.longitudinalFeed]} empty="No validation health rows." compact />
                </div>
              </details>
            </div>
          </div>
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">SECTIONAL INTEGRITY</div>
          <MetricGrid
            rows={[
              ["Coverage", `${sectionalSummary.availableRows}/${sectionalSummary.catalogueRows}`, `${sectionalSummary.schemaRows} schema rows`, toneFrom(sectionalSummary.availableRows ? "GOOD" : "WARN")],
              ["Validation", `${sectionalSummary.matchedRows} matched`, `${sectionalSummary.validationCoverage}% coverage`, toneFrom(sectionalSummary.badRows ? "WARN" : "GOOD")],
              ["Missing / bad", `${sectionalSummary.missingRows} missing`, `${sectionalSummary.badRows} bad`, toneFrom(sectionalSummary.missingRows || sectionalSummary.badRows ? "WARN" : "GOOD")],
              ["Trusted identity", `${sectionalSummary.trustedRows} trusted`, `${sectionalSummary.likelyRows} likely`, toneFrom(sectionalSummary.trustedRows ? "GOOD" : "WARN")],
              ["Unmatched", `${sectionalSummary.unmatchedRows} unmatched`, `${sectionalSummary.duplicateConflicts} conflicts`, toneFrom(sectionalSummary.unmatchedRows || sectionalSummary.duplicateConflicts ? "WARN" : "GOOD")],
              ["Canonical master", `${sectionalSummary.masterRows} rows`, `${sectionalSummary.modellingRows} modelling-safe`, toneFrom(sectionalSummary.modellingRows ? "GOOD" : "WARN")],
              ["Payload recovery", `${sectionalSummary.reconstructionRecovered} recovered`, `${sectionalSummary.reconstructionSuccess}% success`, toneFrom(sectionalSummary.reconstructionRecovered ? "GOOD" : "WARN")],
              ["Physics", `${sectionalSummary.physicsTrusted} trusted`, `${sectionalSummary.physicsBroken} broken`, toneFrom(sectionalSummary.physicsBroken ? "WARN" : "GOOD")],
            ]}
          />
          <details className="edgeiq-audit-details">
            <summary>Sectional distribution</summary>
            <div className="edgeiq-audit-details-body">
              <Distribution rows={groupCount(sectionalValidationRows, "sectional_quality_grade")} empty="No sectional validation rows." />
            </div>
          </details>
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">IDENTITY / FIELD MATCH</div>
          <MetricGrid
            rows={[
              ["Aliases", `${identitySummary.horseAliases} horse`, `${identitySummary.trackAliases} track`, toneFrom(Number(identitySummary.horseAliases) && Number(identitySummary.trackAliases) ? "GOOD" : "WARN")],
              ["Field match", `${identitySummary.fieldTrusted} trusted`, `${identitySummary.fieldLikely} likely`, toneFrom(identitySummary.fieldTrusted ? "GOOD" : "WARN")],
              ["Field unmatched", identitySummary.fieldUnmatched, "race group misses", toneFrom(identitySummary.fieldUnmatched ? "WARN" : "GOOD")],
              ["Identity v2", `${identitySummary.v2Trusted} trusted`, `${identitySummary.v2Ambiguous} ambiguities`, toneFrom(identitySummary.v2Trusted ? "GOOD" : "WARN")],
              ["Runner trust", `${identitySummary.runnerTrusted} trusted`, `${identitySummary.runnerExecutionSafe} execution-safe`, toneFrom(identitySummary.runnerExecutionSafe ? "GOOD" : "WARN")],
              ["Graph quality", `${identitySummary.graphSuccess}% success`, `${identitySummary.conflicts} conflicts`, toneFrom(identitySummary.conflicts ? "WARN" : "GOOD")],
            ]}
          />
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">EXECUTION TRUTH / MEMORY</div>
          <MetricGrid
            rows={[
              ["Execute", String(executionSummary.execute), `${executionRows.length} execution rows`, toneFrom(executionSummary.execute ? "GOOD" : "WARN")],
              ["Rejected", String(executionSummary.rejected), "suppressed / no-price / scratched", toneFrom(executionSummary.rejected ? "WARN" : "GOOD")],
              ["Pending results", String(executionSummary.pending), `${truthRows.length} truth-loop rows`, toneFrom(executionSummary.pending ? "WARN" : "GOOD")],
              ["Positive CLV", String(executionSummary.positiveClv), `${clvRows.length} CLV rows`, toneFrom(executionSummary.positiveClv ? "GOOD" : "WARN")],
              ["Late moves", String(executionSummary.lateMoves), `${tapeRows.length} tape rows`, toneFrom(executionSummary.lateMoves ? "WARN" : "NEUTRAL")],
            ]}
          />
          <CompactList label="Decision distribution" rows={decisionDistribution} />
          <CompactList label="Accountability grades" rows={accountabilityDistribution} />
          <CompactList label="Market movement" rows={movementDistribution} />
          <CompactList label="Execution quality" rows={qualityDistribution} />
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">ACCOUNTABILITY / HEALTH</div>
          <CompactTable title="Accountability summary" rows={accountabilityRows} empty="No accountability rows generated yet." />
          <CompactTable title="CLV sample" rows={clvRowsTop} empty="CLV memory has not accumulated enough sample yet." compact />
          <CompactTable title="Pipeline warnings" rows={healthWarnings} empty="No pipeline health warnings." compact />
        </section>
      </div>
    </div>
  );
}

function TerminalStat({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  sub: string;
  tone?: Tone;
}): React.ReactElement {
  const className =
    tone === "good"
      ? "text-emerald-300"
      : tone === "warn"
        ? "text-amber-300"
        : tone === "bad"
          ? "text-rose-300"
          : "";

  return (
    <div className="edgeiq-terminal-stat">
      <div className="edgeiq-terminal-stat-label">{label}</div>
      <div className={`edgeiq-terminal-stat-value ${className}`}>{value}</div>
      <div className="edgeiq-terminal-stat-sub">{sub}</div>
    </div>
  );
}

function CompactTable({
  title,
  rows,
  empty,
  compact = false,
}: {
  title: string;
  rows: CsvRow[];
  empty: string;
  compact?: boolean;
}): React.ReactElement {
  return (
    <div>
      <div className="edgeiq-panel-title">{title}</div>
      <div className="edgeiq-compact-table">
        {rows.length ? rows.map((row, index) => {
          const rank = clean(row.display_rank) || clean(row.priority_rank) || String(index + 1);
          const headline =
            clean(row.headline)
            || clean(row.check_name)
            || clean(row.horse)
            || clean(row.decision_group)
            || clean(row.panel)
            || clean(row.summary)
            || "Research row";
          const detail =
            clean(row.detail)
            || clean(row.notes)
            || clean(row.message)
            || clean(row.track)
            || clean(row.research_category)
            || clean(row.execution_quality)
            || clean(row.runner_drift_profile);
          const second =
            clean(row.recommended_action)
            || clean(row.status)
            || clean(row.accountability_grade)
            || clean(row.result_status)
            || clean(row.clv_achieved_pct)
            || clean(row.priority_status)
            || clean(row.rows);
          const strong =
            clean(row.research_priority_score)
            || clean(row.severity)
            || clean(row.pnl)
            || clean(row.evidence_rows)
            || clean(row.file)
            || clean(row.clv_result)
            || clean(row.summary);
          return (
            <div className="edgeiq-compact-row" key={`${title}-${headline}-${index}`}>
              <span className="rank">{rank}</span>
              <span className="title">
                {headline}
                {detail ? <div className="detail">{detail}</div> : null}
              </span>
              <span>{second || (compact ? "-" : "Monitor")}</span>
              <span>{compact ? "-" : display(row.research_category || row.track || row.file || row.panel, "-")}</span>
              <span className={toneFrom(strong || second) === "good" ? "text-emerald-300" : toneFrom(strong || second) === "warn" ? "text-amber-300" : toneFrom(strong || second) === "bad" ? "text-rose-300" : ""}>
                {strong || "-"}
              </span>
            </div>
          );
        }) : <div className="edgeiq-empty-state">{empty}</div>}
      </div>
    </div>
  );
}

function MetricGrid({
  rows,
}: {
  rows: Array<[string, string, string, Tone]>;
}): React.ReactElement {
  return (
    <div className="edgeiq-compact-table">
      {rows.map(([label, primary, secondary, tone]) => (
        <div className="edgeiq-compact-row" key={`${label}-${primary}`}>
          <span className="rank">•</span>
          <span className="title">
            {label}
            <div className="detail">{secondary}</div>
          </span>
          <span>{primary}</span>
          <span>{secondary}</span>
          <span className={tone === "good" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : tone === "bad" ? "text-rose-300" : ""}>
            {tone.toUpperCase()}
          </span>
        </div>
      ))}
    </div>
  );
}

function CompactList({
  label,
  rows,
}: {
  label: string;
  rows: Array<[string, number]>;
}): React.ReactElement {
  return (
    <div>
      <div className="edgeiq-panel-title">{label}</div>
      <Distribution rows={rows.slice(0, 6)} empty={`No ${label.toLowerCase()} rows.`} />
    </div>
  );
}

function Distribution({
  rows,
  empty,
}: {
  rows: Array<[string, number]>;
  empty: string;
}): React.ReactElement {
  return (
    <div className="edgeiq-compact-table">
      {rows.length ? rows.map(([value, count], index) => (
        <div className="edgeiq-compact-row" key={`${value}-${count}`}>
          <span className="rank">{index + 1}</span>
          <span className="title">{value}</span>
          <span>{count} rows</span>
          <span>distribution</span>
          <span className={toneFrom(value) === "good" ? "text-emerald-300" : toneFrom(value) === "warn" ? "text-amber-300" : toneFrom(value) === "bad" ? "text-rose-300" : ""}>
            {value}
          </span>
        </div>
      )) : <div className="edgeiq-empty-state">{empty}</div>}
    </div>
  );
}
