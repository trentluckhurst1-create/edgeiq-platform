import type { OperationalRaceState } from "./operational-state";
import { composeExecutiveBrief } from "./executive-brief";
import { buildAssessmentJourney } from "./assessment-journey";


export type CommandDecisionDriver = {
  title: string;
  summary: string;
  priority: string;
};

export type CommandRisk = {
  title: string;
  severity: string;
};

export type CommandEvidenceSummary = {
  ready: number;
  total: number;
  coveragePct: number;
};

export type CommandViewModel = {

  hero: {
    decision: string;
    confidence: number;
    headline: string;
    summary: string;
    action: string;
  };

  journey: ReturnType<typeof buildAssessmentJourney>;

  decisionDrivers: CommandDecisionDriver[];

  risks: CommandRisk[];

  evidence: CommandEvidenceSummary;

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
        .map(alert => ({

          title: alert.title,

          severity: alert.severity,

        })),

    evidence: (() => {

      const ready =
        raceState.feedHealth.filter(
          feed => feed.status==="READY"
        ).length;

      const total =
        raceState.feedHealth.length;

      return {

        ready,

        total,

        coveragePct:
          total === 0
            ? 0
            : Math.round((ready/total)*100),

      };

    })(),

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
