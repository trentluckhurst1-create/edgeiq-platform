from pathlib import Path

vm = Path("src/edgeiq-os/services/command-view-model.ts")

text = vm.read_text(encoding="utf-8")

if "CommandDecisionDriver" not in text:

    text = text.replace(
        "export type CommandViewModel = {",
        """
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
"""
    )

    text = text.replace(
        """  decisionDrivers: {
    title: string;
    summary: string;
    priority: string;
  }[];

  risks: string[];

  evidence: {
    ready: number;
    total: number;
  };
""",
        """  decisionDrivers: CommandDecisionDriver[];

  risks: CommandRisk[];

  evidence: CommandEvidenceSummary;
"""
    )

    text = text.replace(
        """    risks:
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
""",
        """    risks:
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
"""
    )

    vm.write_text(text, encoding="utf-8")

print("[EDGEIQ] Command View Model V2 built")
