from pathlib import Path

adapters_dir = Path("src/edgeiq-os/services/adapters")

# ------------------------------------------------------------------
# RaceShapeAdapter snapshot-driven
# ------------------------------------------------------------------

(adapters_dir / "RaceShapeAdapter.ts").write_text(r'''
import { pick, toNumber } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const RACE_SHAPE_SOURCE = "/data/edgeiq_race_shape_story_v1.csv";

export const RaceShapeAdapter: IntelligenceAdapter = {
  key: "race-shape",
  label: "Race Shape",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const firstRace = snapshot.raceShape[0];

    if (!firstRace) {
      return {
        key: "race-shape",
        label: "Race Shape",
        category: "PACE",
        status: "PARTIAL",
        confidence: 30,
        importance: 90,
        evidence: [
          {
            id: "race-shape-active-race-gap",
            category: "PACE",
            title: "Race Shape active race gap",
            summary: `No race shape row found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
            confidence: 30,
            importance: 90,
            status: "PARTIAL",
          },
        ],
        feedHealth: {
          key: "race-shape",
          label: "Race Shape",
          status: "PARTIAL",
          freshness: `Snapshot active race ${snapshot.context.track} R${snapshot.context.raceNo}; no match`,
        },
      };
    }

    const tempo = pick(firstRace, ["tempo"], "UNKNOWN");
    const story = pick(firstRace, ["race_shape_story"], "Race shape story pending.");
    const label = pick(firstRace, ["race_shape_label"], "Race Shape");
    const leaders = pick(firstRace, ["likely_leaders"], "No leader profile available");
    const paceAdvantage = pick(firstRace, ["pace_advantage_runner"], "Not identified");
    const pressureRisk = pick(firstRace, ["pressure_risk_runner"], "Not identified");
    const leaderCount = toNumber(firstRace.leader_count, 0);
    const onPaceCount = toNumber(firstRace.on_pace_count, 0);
    const runnerCount = toNumber(firstRace.runner_count, snapshot.raceShape.length);

    const pressureConfidence = Math.min(95, 55 + leaderCount * 8 + onPaceCount * 2);

    return {
      key: "race-shape",
      label: "Race Shape",
      category: "PACE",
      status: "READY",
      confidence: pressureConfidence,
      importance: 95,
      evidence: [
        {
          id: "race-shape-story",
          category: "PACE",
          title: `${label} · ${tempo}`,
          summary: story,
          confidence: pressureConfidence,
          importance: 95,
          status: "READY",
        },
        {
          id: "race-shape-leaders",
          category: "PACE",
          title: "Likely leaders",
          summary: leaders,
          confidence: pressureConfidence,
          importance: 85,
          status: "READY",
        },
        {
          id: "race-shape-pressure",
          category: "PACE",
          title: "Map advantage / pressure risk",
          summary: `Map advantage: ${paceAdvantage}. Pressure risk: ${pressureRisk}.`,
          confidence: pressureConfidence,
          importance: 80,
          status: "READY",
        },
      ],
      feedHealth: {
        key: "race-shape",
        label: "Race Shape",
        status: "READY",
        freshness: `Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${runnerCount} runners`,
      },
    };
  },
};
''', encoding="utf-8")

# ------------------------------------------------------------------
# RunnerDNAAdapter snapshot-driven
# ------------------------------------------------------------------

(adapters_dir / "RunnerDNAAdapter.ts").write_text(r'''
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const RUNNERDNAADAPTER_SOURCE = "/data/edgeiq_runner_dna_drawer_feed_v2.csv";

export const RunnerDNAAdapter: IntelligenceAdapter = {
  key: "runner-dna",
  label: "Runner DNA",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.runnerDna;
    const row = rows[0];

    if (!row) {
      return {
        key: "runner-dna",
        label: "Runner DNA",
        category: "RUNNER_DNA",
        status: "PARTIAL",
        confidence: 30,
        importance: 90,
        evidence: [
          {
            id: "runner-dna-active-race-gap",
            category: "RUNNER_DNA",
            title: "Runner DNA active race gap",
            summary: `No Runner DNA rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
            confidence: 30,
            importance: 90,
            status: "PARTIAL",
          },
        ],
        feedHealth: {
          key: "runner-dna",
          label: "Runner DNA",
          status: "PARTIAL",
          freshness: `Snapshot active race ${snapshot.context.track} R${snapshot.context.raceNo}; no match`,
        },
      };
    }

    const horse = pick(row, ["horse"], "Reference runner");
    const dnaBand = pick(row, ["dna_v6_2_band", "dna_band"], "UNKNOWN");
    const dnaNarrative = pick(row, ["runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative", "impact_explanation"], "DNA narrative unavailable.");
    const positive = pick(row, ["positive_1_factor"], "No primary strength identified");
    const risk = pick(row, ["negative_1_factor"], "No primary risk identified");

    return {
      key: "runner-dna",
      label: "Runner DNA",
      category: "RUNNER_DNA",
      status: "READY",
      confidence: 80,
      importance: 90,
      evidence: [
        {
          id: "runner-dna-reference",
          category: "RUNNER_DNA",
          title: `${horse} · DNA ${dnaBand}`,
          summary: dnaNarrative,
          confidence: 80,
          importance: 90,
          status: "READY",
        },
        {
          id: "runner-dna-strength",
          category: "RUNNER_DNA",
          title: "Primary DNA strength",
          summary: positive,
          confidence: 75,
          importance: 85,
          status: "READY",
        },
        {
          id: "runner-dna-risk",
          category: "RUNNER_DNA",
          title: "Primary DNA risk",
          summary: risk,
          confidence: 75,
          importance: 80,
          status: "READY",
        },
      ],
      feedHealth: {
        key: "runner-dna",
        label: "Runner DNA",
        status: "READY",
        freshness: `Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${rows.length} runners`,
      },
    };
  },
};
''', encoding="utf-8")

# ------------------------------------------------------------------
# ExplainabilityAdapter snapshot-driven
# ------------------------------------------------------------------

(adapters_dir / "ExplainabilityAdapter.ts").write_text(r'''
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
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
          freshness: `Snapshot active race ${snapshot.context.track} R${snapshot.context.raceNo}; no match`,
        },
      };
    }

    const horse = pick(row, ["horse"], "Reference runner");
    const why = pick(row, ["why_ranked_here"], "Why-ranked explanation unavailable.");
    const profile = pick(row, ["runner_profile_summary"], "Runner profile unavailable.");
    const confidence = pick(row, ["confidence_explanation"], "Confidence explanation unavailable.");
    const trend = pick(row, ["trend_summary"], "Trend unavailable.");

    return {
      key: "explainability",
      label: "Explainability",
      category: "GENERIC",
      status: "READY",
      confidence: 80,
      importance: 90,
      evidence: [
        {
          id: "explainability-why-ranked",
          category: "GENERIC",
          title: `${horse} · Why ranked`,
          summary: why,
          confidence: 80,
          importance: 90,
          status: "READY",
        },
        {
          id: "explainability-profile",
          category: "GENERIC",
          title: "Runner profile",
          summary: profile,
          confidence: 75,
          importance: 85,
          status: "READY",
        },
        {
          id: "explainability-confidence",
          category: "GENERIC",
          title: "Confidence explanation",
          summary: confidence,
          confidence: 75,
          importance: 80,
          status: "READY",
        },
        {
          id: "explainability-trend",
          category: "GENERIC",
          title: "Trend",
          summary: trend,
          confidence: 70,
          importance: 75,
          status: "READY",
        },
      ],
      feedHealth: {
        key: "explainability",
        label: "Explainability",
        status: "READY",
        freshness: `Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${rows.length} runners`,
      },
    };
  },
};
''', encoding="utf-8")

print("[EDGEIQ] Core adapters refactored to IntelligenceSnapshot")
