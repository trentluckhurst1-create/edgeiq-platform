
import type { OperationalEvidenceItem } from "../operational-state";
import type { CorrelationSummary } from "../operational-correlation";
import type { OperationalFinding } from "./OperationalReasoningTypes";

function byCategory(evidence: OperationalEvidenceItem[], category: string) {
  return evidence.filter((item) => item.category === category);
}

function topSummary(items: OperationalEvidenceItem[]) {
  return items[0]?.summary ?? "";
}

export function buildOperationalFindings(
  evidence: OperationalEvidenceItem[],
  correlation: CorrelationSummary,
): OperationalFinding[] {
  const findings: OperationalFinding[] = [];

  const pace = byCategory(evidence, "PACE");
  const dna = byCategory(evidence, "RUNNER_DNA");
  const market = byCategory(evidence, "MARKET");
  const sectionals = byCategory(evidence, "SECTIONALS");
  const track = byCategory(evidence, "TRACK");
  const weather = byCategory(evidence, "WEATHER");
  const connections = byCategory(evidence, "CONNECTIONS");

  if (pace.length && dna.length && sectionals.length) {
    findings.push({
      id: "pace-dna-sectionals-reinforcement",
      title: "Race shape and runner profile reinforcement",
      summary: `${topSummary(pace)} ${topSummary(dna)} ${topSummary(sectionals)}`,
      confidence: Math.min(95, correlation.operationalConfidence + 5),
      importance: 98,
      priority: "CRITICAL",
      supportingEngines: ["Race Shape", "Runner DNA", "Sectionals"],
    });
  }

  if (market.length && (pace.length || dna.length)) {
    findings.push({
      id: "market-intelligence-relationship",
      title: "Market relationship requires attention",
      summary: `${topSummary(market)} ${topSummary(pace.length ? pace : dna)}`,
      confidence: Math.min(92, correlation.operationalConfidence + 2),
      importance: 92,
      priority: "HIGH",
      supportingEngines: ["Market", pace.length ? "Race Shape" : "Runner DNA"],
    });
  }

  if (track.length || weather.length) {
    findings.push({
      id: "environmental-context",
      title: "Environment context",
      summary: `${topSummary(track)} ${topSummary(weather)}`.trim(),
      confidence: Math.max(45, correlation.operationalConfidence - 5),
      importance: 84,
      priority: "NORMAL",
      supportingEngines: [
        ...(track.length ? ["Track"] : []),
        ...(weather.length ? ["Weather"] : []),
      ],
    });
  }

  if (connections.length) {
    findings.push({
      id: "connection-context",
      title: "Connections context",
      summary: topSummary(connections),
      confidence: Math.max(50, correlation.operationalConfidence - 4),
      importance: 82,
      priority: "NORMAL",
      supportingEngines: ["Connections"],
    });
  }

  if (!findings.length) {
    findings.push({
      id: "limited-operational-reasoning",
      title: "Limited operational reasoning",
      summary: "Insufficient aligned evidence is available to generate a reinforced operational finding.",
      confidence: correlation.operationalConfidence,
      importance: 60,
      priority: "LOW",
      supportingEngines: correlation.supportingModules,
    });
  }

  return findings.sort((a, b) => b.importance - a.importance);
}
