
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import { describeFeedMatch } from "../feed-diagnostics";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const TRACKADAPTER_SOURCE = "/data/edgeiq_live_track_intelligence_v2_1.csv";

export const TrackAdapter: IntelligenceAdapter = {
  key: "track",
  label: "Track Intelligence",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.track;
    const row = rows[0];

    if (!row) {
      return {
        key: "track",
        label: "Track Intelligence",
        category: "TRACK",
        status: "PARTIAL",
        confidence: 30,
        importance: 85,
        evidence: [{
          id: "track-gap",
          category: "TRACK",
          title: "Track active race gap",
          summary: `No Track rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
          confidence: 30,
          importance: 85,
          status: "PARTIAL",
        }],
        feedHealth: { key: "track", label: "Track Intelligence", status: "PARTIAL", freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics") },
      };
    }

    const horse = pick(row, ["horse"], "Reference runner");
    const label = pick(row, ["track_intelligence_label_v2_1"], "UNKNOWN");
    const comment = pick(row, ["track_intelligence_comment_v2_1"], "Track comment unavailable.");
    const fit = pick(row, ["track_fit_band"], "UNKNOWN");
    const score = pick(row, ["track_fit_score"], "UNKNOWN");
    const styleAlign = pick(row, ["run_style_alignment"], "UNKNOWN");
    const barrierAlign = pick(row, ["barrier_alignment"], "UNKNOWN");
    const movementAlign = pick(row, ["movement_alignment"], "UNKNOWN");
    const condition = pick(row, ["track_condition"], "UNKNOWN");
    const rail = pick(row, ["rail_position"], "UNKNOWN");

    return {
      key: "track",
      label: "Track Intelligence",
      category: "TRACK",
      status: "READY",
      confidence: 78,
      importance: 88,
      evidence: [
        { id: "track-read", category: "TRACK", title: `${horse} - ${label}`, summary: comment, confidence: 78, importance: 92, status: "READY" },
        { id: "track-fit", category: "TRACK", title: `Track fit - ${fit}`, summary: `Track fit score ${score}. Condition ${condition}. Rail ${rail}.`, confidence: 76, importance: 88, status: "READY" },
        { id: "track-alignment", category: "TRACK", title: "Track alignment", summary: `Run style ${styleAlign}. Barrier ${barrierAlign}. Movement ${movementAlign}.`, confidence: 74, importance: 84, status: "READY" },
      ],
      feedHealth: { key: "track", label: "Track Intelligence", status: "READY", freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics") },
    };
  },
};
