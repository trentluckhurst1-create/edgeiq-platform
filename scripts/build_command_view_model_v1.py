from pathlib import Path

service = Path("src/edgeiq-os/services/command-view-model.ts")

service.write_text(r'''
import type { OperationalRaceState } from "./operational-state";
import { composeExecutiveBrief } from "./executive-brief";
import { buildAssessmentJourney } from "./assessment-journey";

export type CommandViewModel = {
  hero: {
    decision: string;
    confidence: number;
    headline: string;
    summary: string;
    action: string;
  };

  journey: ReturnType<typeof buildAssessmentJourney>;

  decisionDrivers: {
    title: string;
    summary: string;
    priority: string;
  }[];

  risks: string[];

  evidence: {
    ready: number;
    total: number;
  };

  timeline: {
    time: string;
    title: string;
    detail: string;
  }[];
};

export function buildCommandViewModel(
  raceState: OperationalRaceState,
): CommandViewModel {

  const brief = composeExecutiveBrief(raceState);

  const journey = buildAssessmentJourney(raceState);

  return {

    hero: {

      decision: raceState.decision.state,

      confidence: raceState.confidence,

      headline: raceState.decision.headline,

      summary: brief.currentSituation,

      action: brief.recommendedAction,

    },

    journey,

    decisionDrivers:
      raceState.findings
        .slice(0,5)
        .map(finding => ({

          title: finding.title,

          summary: finding.summary,

          priority: finding.priority,

        })),

    risks:
      raceState.alerts
        .slice(0,4)
        .map(alert => alert.title),

    evidence: {

      ready:
        raceState.feedHealth.filter(
          feed => feed.status==="READY"
        ).length,

      total:
        raceState.feedHealth.length,

    },

    timeline:
      raceState.events
        .slice(0,8)
        .map(event => ({

          time: event.time,

          title: event.title,

          detail: event.detail,

        })),

  };

}
'''.lstrip(), encoding="utf-8")

print("[EDGEIQ] Command View Model built")
