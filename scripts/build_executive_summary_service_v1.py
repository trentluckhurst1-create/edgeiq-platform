from pathlib import Path

root = Path("src/edgeiq-os/services/executive-summary")
root.mkdir(parents=True, exist_ok=True)

(root / "ExecutiveSummaryTypes.ts").write_text(r'''
import type { OperationalDecision } from "../operational-decision";
import type { OperationalFinding } from "../operational-reasoning";
import type { CorrelationSummary } from "../operational-correlation";

export interface ExecutiveSummary {
  decision: OperationalDecision;
  correlation: CorrelationSummary;

  headline: string;
  summary: string;

  topFindings: OperationalFinding[];

  systemHealth: {
    feedsReady: number;
    feedsTotal: number;
    alerts: number;
    coverage: number;
  };
}
''', encoding="utf-8")

(root / "ExecutiveSummaryService.ts").write_text(r'''
import type { IntelligenceFeedHealth } from "../operational-state";
import type { OperationalAlert } from "../alerts";
import type { IntelligenceCoverageItem } from "../operational-state";

import type { OperationalDecision } from "../operational-decision";
import type { OperationalFinding } from "../operational-reasoning";
import type { CorrelationSummary } from "../operational-correlation";

import type { ExecutiveSummary } from "./ExecutiveSummaryTypes";

export function buildExecutiveSummary(
  decision: OperationalDecision,
  findings: OperationalFinding[],
  correlation: CorrelationSummary,
  feedHealth: IntelligenceFeedHealth[],
  alerts: OperationalAlert[],
  coverage: IntelligenceCoverageItem[],
): ExecutiveSummary {

  const readyFeeds =
    feedHealth.filter(f => f.status === "READY").length;

  const coveragePct =
    coverage.length === 0
      ? 0
      : Math.round(
          coverage.reduce((s,c)=>s+c.coveragePct,0) /
          coverage.length
        );

  return {

    decision,

    correlation,

    headline: decision.headline,

    summary: decision.rationale,

    topFindings:
      findings
        .sort((a,b)=>b.importance-a.importance)
        .slice(0,4),

    systemHealth:{

      feedsReady:readyFeeds,

      feedsTotal:feedHealth.length,

      alerts:alerts.length,

      coverage:coveragePct

    }

  };

}
''', encoding="utf-8")

(root / "index.ts").write_text(r'''
export * from "./ExecutiveSummaryTypes";
export * from "./ExecutiveSummaryService";
''', encoding="utf-8")

print("[EDGEIQ] Executive Summary service created")
