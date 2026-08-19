import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type CsvRow = Record<string, string>;
type Tone = "good" | "warn" | "bad" | "neutral";

const FILES = {
  auditSummary: "/data/edgeiq_ecology_research_audit_summary_v1.csv",
  auditFailures: "/data/edgeiq_ecology_research_audit_failures_v1.csv",
  orchestratorSummary: "/data/edgeiq_ecology_orchestrator_summary_v1.csv",
  masterMemorySummary: "/data/edgeiq_ecology_master_memory_orchestrator_summary_v2.csv",
  snapshotSummary: "/data/edgeiq_ecology_snapshot_summary_v1.csv",
  snapshotManifest: "/data/edgeiq_ecology_snapshot_manifest_v1.csv",
  temporalSummary: "/data/edgeiq_ecology_temporal_drift_summary_v1.csv",
  decaySummary: "/data/edgeiq_ecology_memory_decay_summary_v1.csv",
  pressureSummary: "/data/edgeiq_ecology_memory_pressure_summary_v1.csv",
  confidenceSummary: "/data/edgeiq_ecology_memory_confidence_summary_v1.csv",
  maturitySummary: "/data/edgeiq_ecology_memory_maturity_summary_v1.csv",
  resilienceSummary: "/data/edgeiq_ecology_memory_resilience_summary_v1.csv",
  stressSummary: "/data/edgeiq_ecology_memory_stress_summary_v1.csv",
  recoverySummary: "/data/edgeiq_ecology_memory_recovery_summary_v1.csv",
  evolution: "/data/edgeiq_ecology_temporal_evolution_v1.csv",
  evidence: "/data/edgeiq_ecology_evidence_accumulation_v1.csv",
  evidenceSummary: "/data/edgeiq_ecology_evidence_summary_v1.csv",
  governance: "/data/edgeiq_ecology_governance_gate_v1.csv",
  governanceSummary: "/data/edgeiq_ecology_governance_summary_v1.csv",
  approved: "/data/edgeiq_ecology_approved_research_structures_v1.csv",
  blocked: "/data/edgeiq_ecology_blocked_structures_v1.csv",
  ledger: "/data/edgeiq_ecology_research_ledger_v1.csv",
  ledgerSummary: "/data/edgeiq_ecology_research_ledger_summary_v1.csv",
  report: "/data/edgeiq_ecology_daily_report.md",
};

function clean(value: unknown): string {
  const output = String(value ?? "").trim();
  return output && !["NAN", "NULL", "UNDEFINED"].includes(output.toUpperCase()) ? output : "";
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function display(value: unknown, fallback = "Not available"): string {
  return clean(value) || fallback;
}

function metric(rows: CsvRow[], key: string): string {
  return clean(rows.find((row) => clean(row.metric) === key)?.value);
}

function countMetric(rows: CsvRow[], key: string, fallback = "0"): string {
  return display(metric(rows, key), fallback);
}

function toneFrom(value: unknown): Tone {
  const status = upper(value);
  if (!status) return "neutral";
  if (
    status.includes("FAIL")
    || status.includes("BLOCKED")
    || status.includes("REJECT")
    || status.includes("STRESS_FAILURE")
  ) {
    return "bad";
  }
  if (
    status.includes("WARN")
    || status.includes("PRESSURE")
    || status.includes("EARLY")
    || status.includes("LOW")
    || status.includes("WATCH")
    || status.includes("ELEVATED")
    || status.includes("FRAGILE")
    || status.includes("DEGRADED")
  ) {
    return "warn";
  }
  if (
    status.includes("PASS")
    || status.includes("HEALTHY")
    || status.includes("APPROVED")
    || status.includes("STABLE")
    || status.includes("YES")
    || status.includes("PERSIST")
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

async function readOptionalText(path: string): Promise<string> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return "";
    return await response.text();
  } catch {
    return "";
  }
}

function reportGeneratedAt(markdown: string): string {
  const match = markdown.match(/^Generated:\s*(.+)$/m);
  return match?.[1]?.trim() ?? "";
}

function reportStatus(markdown: string): string {
  if (!clean(markdown)) return "REPORT_UNAVAILABLE";
  return "REPORT_AVAILABLE";
}

function compactRows(rows: CsvRow[], limit: number): CsvRow[] {
  return rows.slice(0, limit);
}

export default function EcologyResearchPanel(): React.ReactElement {
  const [data, setData] = useState<Record<string, CsvRow[]>>({});
  const [dailyReport, setDailyReport] = useState("");

  useEffect(() => {
    let alive = true;

    async function load(): Promise<void> {
      const csvEntries = await Promise.all(
        Object.entries(FILES)
          .filter(([key]) => key !== "report")
          .map(async ([key, path]) => [key, await readCsv(path)] as const),
      );
      const reportText = await readOptionalText(FILES.report);
      if (!alive) return;
      setData(Object.fromEntries(csvEntries));
      setDailyReport(reportText);
    }

    load();
    const timer = window.setInterval(load, 90000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const auditSummary = data.auditSummary ?? [];
  const auditFailures = data.auditFailures ?? [];
  const orchestratorSummary = data.orchestratorSummary ?? [];
  const masterMemorySummary = data.masterMemorySummary ?? [];
  const snapshotSummary = data.snapshotSummary ?? [];
  const snapshotManifest = data.snapshotManifest ?? [];
  const temporalSummary = data.temporalSummary ?? [];
  const decaySummary = data.decaySummary ?? [];
  const pressureSummary = data.pressureSummary ?? [];
  const confidenceSummary = data.confidenceSummary ?? [];
  const maturitySummary = data.maturitySummary ?? [];
  const resilienceSummary = data.resilienceSummary ?? [];
  const stressSummary = data.stressSummary ?? [];
  const recoverySummary = data.recoverySummary ?? [];
  const evolution = data.evolution ?? [];
  const evidence = data.evidence ?? [];
  const evidenceSummary = data.evidenceSummary ?? [];
  const governance = data.governance ?? [];
  const governanceSummary = data.governanceSummary ?? [];
  const approved = data.approved ?? [];
  const blocked = data.blocked ?? [];
  const ledger = data.ledger ?? [];
  const ledgerSummary = data.ledgerSummary ?? [];

  const boundary = display(
    metric(masterMemorySummary, "research_boundary") || metric(snapshotSummary, "research_boundary"),
    "OFFLINE_RESEARCH_ONLY",
  );
  const liveModelling = countMetric(masterMemorySummary, "live_modelling_yes");
  const liveExecution = countMetric(masterMemorySummary, "live_execution_yes");
  const reportGenerated = reportGeneratedAt(dailyReport);

  const memoryLayers = [
    {
      label: "Master memory",
      value: display(metric(masterMemorySummary, "overall_stack_health"), "Unknown"),
      detail: `${countMetric(masterMemorySummary, "pipeline_passed")}/${countMetric(masterMemorySummary, "pipeline_steps")} passed`,
    },
    {
      label: "Temporal memory",
      value: display(metric(temporalSummary, "overall_temporal_memory_health"), "Unknown"),
      detail: `${countMetric(temporalSummary, "snapshot_count")} snapshots`,
    },
    {
      label: "Decay",
      value: display(metric(decaySummary, "overall_decay_health"), "Unknown"),
      detail: `${countMetric(decaySummary, "low_decay_risk_rows")} low-risk rows`,
    },
    {
      label: "Pressure",
      value: display(metric(pressureSummary, "overall_pressure_health"), "Unknown"),
      detail: `${countMetric(pressureSummary, "alert_rows")} alerts`,
    },
    {
      label: "Confidence",
      value: display(metric(confidenceSummary, "overall_confidence_health"), "Unknown"),
      detail: `${countMetric(confidenceSummary, "alert_rows")} alerts`,
    },
    {
      label: "Maturity",
      value: display(metric(maturitySummary, "overall_maturity_health"), "Unknown"),
      detail: `${countMetric(maturitySummary, "early_memory_rows")} early rows`,
    },
    {
      label: "Resilience",
      value: display(metric(resilienceSummary, "overall_resilience_health"), "Unknown"),
      detail: `${countMetric(resilienceSummary, "low_resilience_rows")} low-resilience rows`,
    },
    {
      label: "Stress",
      value: display(metric(stressSummary, "overall_stress_health"), "Unknown"),
      detail: `${countMetric(stressSummary, "stress_rows")} stress rows`,
    },
    {
      label: "Recovery",
      value: display(metric(recoverySummary, "overall_recovery_health"), "Unknown"),
      detail: `${countMetric(recoverySummary, "low_recovery_rows")} low-recovery rows`,
    },
  ];

  const summaryCards = [
    {
      label: "Audit",
      value: display(metric(auditSummary, "overall_status"), "Unknown"),
      detail: `${countMetric(auditSummary, "pass_count")} pass · ${countMetric(auditSummary, "warn_count")} warn · ${countMetric(auditSummary, "fail_count")} fail`,
    },
    {
      label: "Orchestrator",
      value: display(metric(orchestratorSummary, "health_status"), "Unknown"),
      detail: `${countMetric(orchestratorSummary, "steps_passed")}/${countMetric(orchestratorSummary, "steps_run")} scripts`,
    },
    {
      label: "Snapshot archive",
      value: display(metric(snapshotSummary, "archive_status"), "Unknown"),
      detail: display(metric(snapshotSummary, "latest_snapshot_id"), "No snapshot"),
    },
    {
      label: "Daily report",
      value: reportStatus(dailyReport),
      detail: reportGenerated || "Report not generated",
    },
    {
      label: "Approved research",
      value: display(metric(ledgerSummary, "approved_for_research_yes"), String(approved.length)),
      detail: `${display(metric(ledgerSummary, "approved_for_research_watchlist"), String(blocked.length))} watchlist / held`,
    },
  ];

  const topEvidence = useMemo(
    () => evidence.find((row) => clean(row.priority_rank) === "1") ?? evidence[0] ?? null,
    [evidence],
  );
  const topGovernance = useMemo(
    () => governance.find((row) => clean(row.governance_rank) === "1") ?? governance[0] ?? null,
    [governance],
  );
  const topEvolution = useMemo(
    () => evolution.find((row) => upper(row.track) === "ROCKHAMPTON") ?? evolution[0] ?? null,
    [evolution],
  );
  const latestSnapshot = useMemo(
    () => snapshotManifest.find((row) => clean(row.source_file) === "edgeiq_ecology_research_ledger_v1.csv") ?? snapshotManifest[0] ?? null,
    [snapshotManifest],
  );

  const ledgerRows = compactRows(ledger, 6);
  const issueRows = compactRows(auditFailures, 5);

  return (
    <section className="edgeiq-panel edgeiq-ecology-terminal">
      <div className="edgeiq-ecology-topline">
        <div>
          <div className="edgeiq-panel-title">QLD ECOLOGY RESEARCH STACK</div>
          <div className="edgeiq-helper-text">
            Offline research memory only. Governance, decay, pressure and resilience stay visible here, and out of execution.
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`edgeiq-pill ${toneFrom(boundary)}`}>{boundary}</span>
          <span className="edgeiq-pill neutral">Model {liveModelling}</span>
          <span className="edgeiq-pill neutral">Exec {liveExecution}</span>
          <a className="edgeiq-ecology-report-link" href={FILES.report} target="_blank" rel="noreferrer">
            Open daily report
          </a>
        </div>
      </div>

      <div className="edgeiq-terminal-banner">
        <strong>Offline research boundary</strong>
        <span>live_modelling_yes = {liveModelling} · live_execution_yes = {liveExecution} · governance remains research-only</span>
      </div>

      <div className="edgeiq-ecology-summary-grid">
        {summaryCards.map((card) => (
          <div className="edgeiq-ecology-summary-card" key={card.label}>
            <span>{card.label}</span>
            <strong className={toneFrom(card.value) === "good" ? "text-emerald-300" : toneFrom(card.value) === "warn" ? "text-amber-300" : toneFrom(card.value) === "bad" ? "text-rose-300" : ""}>
              {card.value}
            </strong>
            <small>{card.detail}</small>
          </div>
        ))}
      </div>

      <div className="edgeiq-ecology-memory-grid">
        {memoryLayers.map((layer) => (
          <div className="edgeiq-ecology-memory-card" key={layer.label}>
            <span>{layer.label}</span>
            <strong className={toneFrom(layer.value) === "good" ? "text-emerald-300" : toneFrom(layer.value) === "warn" ? "text-amber-300" : toneFrom(layer.value) === "bad" ? "text-rose-300" : ""}>
              {layer.value}
            </strong>
            <small>{layer.detail}</small>
          </div>
        ))}
      </div>

      <div className="edgeiq-ecology-columns">
        <section className="edgeiq-terminal-subgrid">
          <div>
            <div className="edgeiq-panel-title">RESEARCH LEDGER</div>
            <div className="edgeiq-compact-table">
              {ledgerRows.length ? ledgerRows.map((row, index) => (
                <div className="edgeiq-compact-row" key={`${clean(row.structure_id)}-${clean(row.track)}-${index}`}>
                  <span className="rank">{index + 1}</span>
                  <span className="title">
                    {display(row.track)}
                    <div className="detail">{display(row.lifecycle_phase, "Lifecycle unavailable")}</div>
                  </span>
                  <span>{display(row.evidence_score, "-")}</span>
                  <span>{display(row.governance_status, "-")}</span>
                  <span className={toneFrom(row.approved_for_research) === "good" ? "text-emerald-300" : toneFrom(row.approved_for_research) === "warn" ? "text-amber-300" : "text-slate-300"}>
                    {display(row.approved_for_research, "NO")}
                  </span>
                </div>
              )) : <div className="edgeiq-empty-state">Research ledger is not available.</div>}
            </div>
          </div>

          <div>
            <div className="edgeiq-panel-title">AUDIT / GOVERNANCE ISSUES</div>
            <div className="edgeiq-compact-table">
              {issueRows.length ? issueRows.map((row, index) => (
                <div className="edgeiq-compact-row" key={`${clean(row.check_name)}-${index}`}>
                  <span className="rank">{index + 1}</span>
                  <span className="title">
                    {display(row.check_name)}
                    <div className="detail">{display(row.reason || row.message, "No detail")}</div>
                  </span>
                  <span>{display(row.severity || row.status, "-")}</span>
                  <span>{display(row.affected_layer || row.source_file, "-")}</span>
                  <span className="text-amber-300">Review</span>
                </div>
              )) : <div className="edgeiq-empty-state">No ecology audit failures reported.</div>}
            </div>
          </div>
        </section>

        <section className="edgeiq-terminal-subgrid">
          <div className="edgeiq-ecology-summary-card">
            <span>Top evidence structure</span>
            <strong>{display(topEvidence?.track, display(metric(evidenceSummary, "top_research_structure"), "Not available"))}</strong>
            <small>{display(topEvidence?.research_maturity_class, display(metric(evidenceSummary, "top_research_maturity"), "Maturity unavailable"))}</small>
          </div>

          <div className="edgeiq-ecology-summary-card">
            <span>Governance focus</span>
            <strong>{display(topGovernance?.track, display(metric(governanceSummary, "top_governance_track"), "Not available"))}</strong>
            <small>{display(topGovernance?.governance_gate_status, display(metric(governanceSummary, "top_governance_status"), "Governance unavailable"))}</small>
          </div>

          <div className="edgeiq-ecology-summary-card">
            <span>Temporal climate</span>
            <strong>{display(topEvolution?.track, "Not available")}</strong>
            <small>{display(topEvolution?.current_climate, "Climate unavailable")} · stability {display(topEvolution?.stability_score, "-")}</small>
          </div>

          <div className="edgeiq-ecology-summary-card">
            <span>Latest snapshot</span>
            <strong>{display(latestSnapshot?.timestamp_utc, "Awaiting archive")}</strong>
            <small>{display(latestSnapshot?.source_file, "Snapshot manifest unavailable")}</small>
          </div>
        </section>
      </div>

      <div className="edgeiq-data-note">
        Daily report: {reportGenerated ? `generated ${reportGenerated}` : "not available"} · approved_for_modelling_yes {display(metric(ledgerSummary, "approved_for_modelling_yes"), "0")} · approved_for_execution_yes {display(metric(ledgerSummary, "approved_for_execution_yes"), "0")}
      </div>
    </section>
  );
}
