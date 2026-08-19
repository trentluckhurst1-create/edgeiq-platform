from pathlib import Path

path = Path("src/edgeiq-os/services/adapters/RaceShapeAdapter.ts")

path.write_text(r'''
import { pick, toNumber } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const RACE_SHAPE_SOURCE = "/data/edgeiq_race_shape_story_v1.csv";

function pressureBand(tempo: string, leaderCount: number, onPaceCount: number): string {
  if (tempo.includes("FAST") || leaderCount >= 3) return "HIGH PRESSURE";
  if (leaderCount >= 2 || onPaceCount >= 5) return "GENUINE";
  return "CONTROLLED";
}

export const RaceShapeAdapter: IntelligenceAdapter = {
  key: "race-shape",
  label: "Race Shape",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const row = snapshot.raceShape[0];

    if (!row) {
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

    const tempo = pick(row, ["tempo"], "UNKNOWN");
    const story = pick(row, ["race_shape_story"], "Race shape story pending.");
    const label = pick(row, ["race_shape_label"], "Race Shape");
    const leaders = pick(row, ["likely_leaders"], "No leader profile available");
    const onPace = pick(row, ["likely_on_pace"], "No on-pace profile available");
    const midfield = pick(row, ["likely_midfield"], "No midfield profile available");
    const backmarkers = pick(row, ["likely_backmarkers"], "No backmarker profile available");
    const paceAdvantage = pick(row, ["pace_advantage_runner"], "Not identified");
    const latePower = pick(row, ["late_power_beneficiary"], "Not identified");
    const pressureRisk = pick(row, ["pressure_risk_runner"], "Not identified");

    const leaderCount = toNumber(row.leader_count, 0);
    const onPaceCount = toNumber(row.on_pace_count, 0);
    const midfieldCount = toNumber(row.midfield_count, 0);
    const backmarkerCount = toNumber(row.backmarker_count, 0);
    const runnerCount = toNumber(row.runner_count, snapshot.raceShape.length);
    const pressure = pressureBand(tempo, leaderCount, onPaceCount);

    const confidence = Math.min(95, 55 + leaderCount * 8 + onPaceCount * 2);

    return {
      key: "race-shape",
      label: "Race Shape",
      category: "PACE",
      status: "READY",
      confidence,
      importance: 95,
      evidence: [
        {
          id: "race-shape-story",
          category: "PACE",
          title: `${label} · ${tempo}`,
          summary: story,
          confidence,
          importance: 100,
          status: "READY",
        },
        {
          id: "race-shape-pressure-band",
          category: "PACE",
          title: `Pressure profile · ${pressure}`,
          summary: `${leaderCount} leader(s), ${onPaceCount} on-pace runner(s), ${midfieldCount} midfield runner(s), ${backmarkerCount} backmarker(s).`,
          confidence,
          importance: 95,
          status: "READY",
        },
        {
          id: "race-shape-leaders",
          category: "PACE",
          title: "Likely leaders",
          summary: leaders,
          confidence,
          importance: 90,
          status: "READY",
        },
        {
          id: "race-shape-on-pace",
          category: "PACE",
          title: "Likely on-pace runners",
          summary: onPace,
          confidence,
          importance: 85,
          status: "READY",
        },
        {
          id: "race-shape-midfield",
          category: "PACE",
          title: "Likely midfield runners",
          summary: midfield,
          confidence,
          importance: 75,
          status: "READY",
        },
        {
          id: "race-shape-backmarkers",
          category: "PACE",
          title: "Likely backmarkers",
          summary: backmarkers,
          confidence,
          importance: 70,
          status: "READY",
        },
        {
          id: "race-shape-map-advantage",
          category: "PACE",
          title: "Map advantage",
          summary: `Map advantage: ${paceAdvantage}. Late-power beneficiary: ${latePower}. Pressure risk: ${pressureRisk}.`,
          confidence,
          importance: 90,
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

print("[EDGEIQ] Race Shape adapter enriched")
