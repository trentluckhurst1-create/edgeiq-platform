
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import { describeFeedMatch } from "../feed-diagnostics";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const MARKETADAPTER_SOURCE = "/data/edgeiq_market_intelligence_v1.csv";

export const MarketAdapter: IntelligenceAdapter = {
  key: "market",
  label: "Market",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.market;
    const row = rows[0];

    if (!row) {
      return {
        key: "market",
        label: "Market",
        category: "MARKET",
        status: "PARTIAL",
        confidence: 30,
        importance: 85,
        evidence: [
          {
            id: "market-active-race-gap",
            category: "MARKET",
            title: "Market active race gap",
            summary: `No Market rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
            confidence: 30,
            importance: 85,
            status: "PARTIAL",
          },
        ],
        feedHealth: {
          key: "market",
          label: "Market",
          status: "PARTIAL",
          freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics"),
        },
      };
    }

    const comment = pick(row, ["market_comment"], "Market comment unavailable.");
    const efficiency = pick(row, ["market_efficiency"], "UNKNOWN");
    const strongestFirmer = pick(row, ["strongest_firmer"], "No clear firmer");
    const largestDrifter = pick(row, ["largest_drifter"], "No clear drifter");
    const overlayCount = pick(row, ["overlay_count"], "0");
    const strongOverlayCount = pick(row, ["strong_overlay_count"], "0");
    const quality = pick(row, ["avg_bet_quality_score"], "UNKNOWN");

    return {
      key: "market",
      label: "Market",
      category: "MARKET",
      status: "READY",
      confidence: 78,
      importance: 92,
      evidence: [
        {
          id: "market-comment",
          category: "MARKET",
          title: `Market state - ${efficiency}`,
          summary: comment,
          confidence: 78,
          importance: 95,
          status: "READY",
        },
        {
          id: "market-movers",
          category: "MARKET",
          title: "Market movers",
          summary: `Strongest firmer: ${strongestFirmer}. Largest drifter: ${largestDrifter}.`,
          confidence: 76,
          importance: 90,
          status: "READY",
        },
        {
          id: "market-overlays",
          category: "MARKET",
          title: "Overlay profile",
          summary: `${overlayCount} positive overlay(s), including ${strongOverlayCount} strong overlay(s). Average quality score: ${quality}.`,
          confidence: 76,
          importance: 88,
          status: "READY",
        },
      ],
      feedHealth: {
        key: "market",
        label: "Market",
        status: "READY",
        freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics"),
      },
    };
  },
};
