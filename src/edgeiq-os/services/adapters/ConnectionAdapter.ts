
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import { describeFeedMatch } from "../feed-diagnostics";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const CONNECTIONADAPTER_SOURCE = "/data/edgeiq_connection_intelligence_v2_1.csv";

export const ConnectionAdapter: IntelligenceAdapter = {
  key: "connections",
  label: "Connections",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.connections;
    const row = rows[0];

    if (!row) {
      return {
        key: "connections",
        label: "Connections",
        category: "CONNECTIONS",
        status: "PARTIAL",
        confidence: 30,
        importance: 85,
        evidence: [{
          id: "connections-gap",
          category: "CONNECTIONS",
          title: "Connections active race gap",
          summary: `No Connections rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
          confidence: 30,
          importance: 85,
          status: "PARTIAL",
        }],
        feedHealth: { key: "connections", label: "Connections", status: "PARTIAL", freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics") },
      };
    }

    const horse = pick(row, ["horse"], "Reference runner");
    const band = pick(row, ["connection_band", "connection_strength"], "UNKNOWN");
    const score = pick(row, ["connection_score"], "UNKNOWN");
    const narrative = pick(row, ["connection_narrative"], "Connection narrative unavailable.");
    const angle1 = pick(row, ["connection_angle_1"], "No primary angle");
    const angle2 = pick(row, ["connection_angle_2"], "No secondary angle");
    const angle3 = pick(row, ["connection_angle_3"], "No third angle");
    const risk = pick(row, ["connection_risk_1"], "No connection risk identified");
    const quality = pick(row, ["evidence_quality"], "UNKNOWN");

    return {
      key: "connections",
      label: "Connections",
      category: "CONNECTIONS",
      status: "READY",
      confidence: 80,
      importance: 88,
      evidence: [
        { id: "connections-narrative", category: "CONNECTIONS", title: `${horse} - Connections ${band}`, summary: `Score ${score}. ${narrative}`, confidence: 80, importance: 92, status: "READY" },
        { id: "connections-angles", category: "CONNECTIONS", title: "Connection angles", summary: `${angle1}. ${angle2}. ${angle3}.`, confidence: 78, importance: 88, status: "READY" },
        { id: "connections-risk", category: "CONNECTIONS", title: "Connection risk", summary: risk, confidence: 76, importance: 84, status: "READY" },
        { id: "connections-quality", category: "CONNECTIONS", title: "Evidence quality", summary: quality, confidence: 74, importance: 78, status: "READY" },
      ],
      feedHealth: { key: "connections", label: "Connections", status: "READY", freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics") },
    };
  },
};
