from pathlib import Path

path = Path("src/edgeiq-os/services/adapters/RunnerDNAAdapter.ts")

path.write_text(r'''
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
    const dnaScore = pick(row, ["dna_v6_2_score", "dna_score"], "UNKNOWN");
    const dnaBand = pick(row, ["dna_v6_2_band", "dna_band"], "UNKNOWN");
    const narrative = pick(row, ["runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative", "impact_explanation"], "DNA narrative unavailable.");
    const strongest = pick(row, ["strongest_factor_v6_2", "strongest_factor_v6_1", "positive_1_factor"], "No primary strength identified");
    const strongestScore = pick(row, ["strongest_factor_score_v6_2", "strongest_factor_score_v6_1", "positive_1_impact"], "");
    const weakest = pick(row, ["weakest_factor_v6_2", "weakest_factor_v6_1", "negative_1_factor"], "No primary risk identified");
    const weakestScore = pick(row, ["weakest_factor_score_v6_2", "weakest_factor_score_v6_1", "negative_1_impact"], "");
    const distance = pick(row, ["distance_fit_band"], "UNKNOWN");
    const condition = pick(row, ["condition_fit_band"], "UNKNOWN");
    const classFit = pick(row, ["class_fit_band"], "UNKNOWN");
    const classMove = pick(row, ["class_movement"], "UNKNOWN");

    return {
      key: "runner-dna",
      label: "Runner DNA",
      category: "RUNNER_DNA",
      status: "READY",
      confidence: 82,
      importance: 92,
      evidence: [
        {
          id: "runner-dna-reference",
          category: "RUNNER_DNA",
          title: `${horse} · DNA ${dnaBand}`,
          summary: `Score ${dnaScore}. ${narrative}`,
          confidence: 82,
          importance: 95,
          status: "READY",
        },
        {
          id: "runner-dna-strength",
          category: "RUNNER_DNA",
          title: "Primary DNA strength",
          summary: `${strongest}${strongestScore ? ` · ${strongestScore}` : ""}`,
          confidence: 78,
          importance: 90,
          status: "READY",
        },
        {
          id: "runner-dna-risk",
          category: "RUNNER_DNA",
          title: "Primary DNA risk",
          summary: `${weakest}${weakestScore ? ` · ${weakestScore}` : ""}`,
          confidence: 78,
          importance: 88,
          status: "READY",
        },
        {
          id: "runner-dna-fit-profile",
          category: "RUNNER_DNA",
          title: "Fit profile",
          summary: `Distance ${distance}. Condition ${condition}. Class ${classFit}. Class movement ${classMove}.`,
          confidence: 76,
          importance: 84,
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

print("[EDGEIQ] Runner DNA adapter enriched")
