
import type {
  IntelligenceCoverageItem,
  OperationalAlert,
  OperationalFeedHealth,
} from "../operational-state";

import type { OperationalDecision } from "../operational-decision";
import type { OperationalFinding } from "../operational-reasoning";
import type { CorrelationSummary } from "../operational-correlation";

import type { ExecutiveSummary } from "./ExecutiveSummaryTypes";

export function buildExecutiveSummary(
  decision: OperationalDecision,
  findings: OperationalFinding[],
  correlation: CorrelationSummary,
  feedHealth: OperationalFeedHealth[],
  alerts: OperationalAlert[],
  coverage: IntelligenceCoverageItem[],
): ExecutiveSummary {
  const readyFeeds = feedHealth.filter((feed) => feed.status === "READY").length;

  const coveragePct =
    coverage.length === 0
      ? 0
      : Math.round(
          coverage.reduce((sum, item) => sum + item.coveragePct, 0) /
            coverage.length,
        );

  return {
    decision,
    correlation,
    headline: decision.headline,
    summary: decision.rationale,
    topFindings: findings.sort((a, b) => b.importance - a.importance).slice(0, 4),
    systemHealth: {
      feedsReady: readyFeeds,
      feedsTotal: feedHealth.length,
      alerts: alerts.length,
      coverage: coveragePct,
    },
  };
}
