
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import { describeFeedMatch } from "../feed-diagnostics";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const EXPLAINABILITYADAPTER_SOURCE = "/data/edgeiq_explainability_terminal_feed_v1_2.csv";

export const ExplainabilityAdapter: IntelligenceAdapter = {
  key: "explainability",
  label: "Explainability",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.explainability;
    const row = rows[0];

    if (!row) {
      return {
        key: "explainability",
        label: "Explainability",
        category: "GENERIC",
        status: "PARTIAL",
        confidence: 30,
        importance: 90,
        evidence: [
          {
            id: "explainability-active-race-gap",
            category: "GENERIC",
            title: "Explainability active race gap",
            summary: `No Explainability rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
            confidence: 30,
            importance: 90,
            status: "PARTIAL",
          },
        ],
        feedHealth: {
          key: "explainability",
          label: "Explainability",
          status: "PARTIAL",
          freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics"),
        },
      };
    }

    const horse = pick(row, ["horse"], "Reference runner");
    const modelRank = pick(row, ["model_rank"], "UNKNOWN");
    const confidenceBand = pick(row, ["confidence_band"], "UNKNOWN");
    const finalConfidence = pick(row, ["final_confidence_score"], "UNKNOWN");
    const why = pick(row, ["why_ranked_here"], "Why-ranked explanation unavailable.");
    const profile = pick(row, ["runner_profile_summary"], "Runner profile unavailable.");
    const confidence = pick(row, ["confidence_explanation"], "Confidence explanation unavailable.");
    const trend = pick(row, ["trend_summary"], "Trend unavailable.");
    const positive1 = pick(row, ["positive_1"], "No primary positive");
    const positive1Value = pick(row, ["positive_1_value"], "");
    const positive2 = pick(row, ["positive_2"], "No secondary positive");
    const positive2Value = pick(row, ["positive_2_value"], "");
    const risk1 = pick(row, ["risk_1"], "No primary risk");
    const risk1Value = pick(row, ["risk_1_value"], "");
    const risk2 = pick(row, ["risk_2"], "No secondary risk");
    const risk2Value = pick(row, ["risk_2_value"], "");
    const connection = pick(row, ["connection_summary_for_decision_engine", "connection_narrative"], "Connection summary unavailable.");
    const marketExpectation = pick(row, ["market_expectation_label"], "Market expectation unavailable.");

    return {
      key: "explainability",
      label: "Explainability",
      category: "GENERIC",
      status: "READY",
      confidence: 84,
      importance: 92,
      evidence: [
        {
          id: "explainability-why-ranked",
          category: "GENERIC",
          title: `${horse} - Why ranked`,
          summary: `Rank #${modelRank}. ${why}`,
          confidence: 84,
          importance: 96,
          status: "READY",
        },
        {
          id: "explainability-confidence",
          category: "GENERIC",
          title: `Confidence - ${confidenceBand}`,
          summary: `Final confidence ${finalConfidence}. ${confidence}`,
          confidence: 82,
          importance: 92,
          status: "READY",
        },
        {
          id: "explainability-positives",
          category: "GENERIC",
          title: "Key positives",
          summary: `${positive1}${positive1Value ? ` ${positive1Value}` : ""}. ${positive2}${positive2Value ? ` ${positive2Value}` : ""}.`,
          confidence: 80,
          importance: 88,
          status: "READY",
        },
        {
          id: "explainability-risks",
          category: "GENERIC",
          title: "Key risks",
          summary: `${risk1}${risk1Value ? ` ${risk1Value}` : ""}. ${risk2}${risk2Value ? ` ${risk2Value}` : ""}.`,
          confidence: 80,
          importance: 88,
          status: "READY",
        },
        {
          id: "explainability-profile",
          category: "GENERIC",
          title: "Runner profile",
          summary: profile,
          confidence: 78,
          importance: 84,
          status: "READY",
        },
        {
          id: "explainability-trend",
          category: "GENERIC",
          title: "Recent trend",
          summary: trend,
          confidence: 76,
          importance: 80,
          status: "READY",
        },
        {
          id: "explainability-connections",
          category: "GENERIC",
          title: "Connection support",
          summary: connection,
          confidence: 76,
          importance: 78,
          status: "READY",
        },
        {
          id: "explainability-market",
          category: "GENERIC",
          title: "Market expectation",
          summary: marketExpectation,
          confidence: 74,
          importance: 76,
          status: "READY",
        },
      ],
      feedHealth: {
        key: "explainability",
        label: "Explainability",
        status: "READY",
        freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics"),
      },
    };
  },
};
