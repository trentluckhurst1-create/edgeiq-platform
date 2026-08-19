
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import { describeFeedMatch } from "../feed-diagnostics";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const SECTIONALSADAPTER_SOURCE = "/data/edgeiq_live_sectional_intelligence_v1.csv";

export const SectionalsAdapter: IntelligenceAdapter = {
  key: "sectionals",
  label: "Sectionals",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.sectionals;
    const row = rows[0];

    if (!row) {
      return {
        key: "sectionals",
        label: "Sectionals",
        category: "SECTIONALS",
        status: "PARTIAL",
        confidence: 30,
        importance: 82,
        evidence: [{
          id: "sectionals-gap",
          category: "SECTIONALS",
          title: "Sectionals active race gap",
          summary: `No Sectionals rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
          confidence: 30,
          importance: 82,
          status: "PARTIAL",
        }],
        feedHealth: { key: "sectionals", label: "Sectionals", status: "PARTIAL", freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics") },
      };
    }

    const horse = pick(row, ["horse_name"], "Reference runner");
    const comment = pick(row, ["sectional_comment"], "Sectional summary unavailable.");
    const status = pick(row, ["sectional_intelligence_status"], "UNKNOWN");
    const archetype = pick(row, ["sectional_archetype"], "UNKNOWN");
    const evidenceType = pick(row, ["sectional_evidence_type"], "UNKNOWN");
    const depth = pick(row, ["profile_depth_status"], "UNKNOWN");
    const runs = pick(row, ["runs_with_sectionals"], "UNKNOWN");
    const early = pick(row, ["avg_early_speed"], "UNKNOWN");
    const mid = pick(row, ["avg_mid_speed"], "UNKNOWN");
    const late = pick(row, ["avg_late_speed"], "UNKNOWN");
    const peak = pick(row, ["avg_peak_speed"], "UNKNOWN");

    return {
      key: "sectionals",
      label: "Sectionals",
      category: "SECTIONALS",
      status: "READY",
      confidence: 78,
      importance: 86,
      evidence: [
        { id: "sectionals-summary", category: "SECTIONALS", title: `${horse} - ${status}`, summary: comment, confidence: 78, importance: 90, status: "READY" },
        { id: "sectionals-archetype", category: "SECTIONALS", title: `Sectional archetype - ${archetype}`, summary: `Evidence type ${evidenceType}. Profile depth ${depth}. Runs with sectionals ${runs}.`, confidence: 76, importance: 86, status: "READY" },
        { id: "sectionals-speed-profile", category: "SECTIONALS", title: "Speed profile", summary: `Early ${early}. Mid ${mid}. Late ${late}. Peak ${peak}.`, confidence: 74, importance: 82, status: "READY" },
      ],
      feedHealth: { key: "sectionals", label: "Sectionals", status: "READY", freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics") },
    };
  },
};
