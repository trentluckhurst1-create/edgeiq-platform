export type CommandFindingTone = "info" | "opportunity" | "risk";

export type CommandFinding = {
  label: string;
  text: string;
  tone: CommandFindingTone;
};

export type CommandContender = {
  role: string;
  title: string;
  detail: string;
};

export type CommandRaceContext = {
  meeting?: string;
  race?: string;
  distance?: string;
  track?: string;
  rail?: string;
  jump?: string;
};

export type CommandExecutiveSummary = {
  assessment: string;
  findings: CommandFinding[];
  contenders: CommandContender[];
  market: {
    overlay: string;
    confidence: string;
    movement: string;
  };
  tactical: {
    speed: string;
    settle: string;
    close: string;
  };
  raceContextStrip?: string[];
};

export function buildCommandExecutiveSummary(raceContext?: CommandRaceContext): CommandExecutiveSummary {
  const hasRaceContext = Boolean(raceContext?.meeting || raceContext?.race);

  return {
    assessment: hasRaceContext
      ? `EDGEiQ COMMAND has assembled ${raceContext?.meeting ?? "the selected meeting"} ${raceContext?.race ?? "race"} into an executive intelligence briefing. The race should be read through tactical position, market behaviour, confidence, opportunity and risk rather than isolated ratings.`
      : "Select a race to activate the full EDGEiQ COMMAND briefing. The executive layer will translate race shape, market behaviour and runner evidence into a professional decision view.",
    findings: [
      {
        label: "Tactical Read",
        text: "The first read is race shape: early speed, settling positions, pressure and where the winning move is likely to form.",
        tone: "info",
      },
      {
        label: "Market Read",
        text: "The market assessment focuses on opportunity and mispricing without exposing EDGEiQ pricing calculations.",
        tone: "opportunity",
      },
      {
        label: "Risk Read",
        text: "Primary risk is separated from opportunity so users understand what could break the race scenario.",
        tone: "risk",
      },
    ],
    contenders: [
      {
        role: "Top Intelligence Call",
        title: "Primary race read",
        detail: "Reserved for the runner with the strongest combined intelligence profile once live race data is connected.",
      },
      {
        role: "Best Opportunity",
        title: "Market overlay",
        detail: "Reserved for the runner where current market price most clearly exceeds assessed opportunity.",
      },
      {
        role: "Main Risk",
        title: "Scenario threat",
        detail: "Reserved for the runner or race condition most likely to disrupt the expected shape.",
      },
    ],
    market: {
      overlay: "Awaiting live selection",
      confidence: "Awaiting live selection",
      movement: "Awaiting live selection",
    },
    tactical: {
      speed: "Barrier Speed",
      settle: "Settling Shape",
      close: "Closing Strength",
    },
    raceContextStrip: [
      raceContext?.meeting ?? "Meeting pending",
      raceContext?.race ?? "Race pending",
      raceContext?.distance ?? "Distance pending",
      raceContext?.track ?? "Track pending",
      raceContext?.rail ?? "Rail pending",
      raceContext?.jump ?? "Jump pending",
    ],
  };
}
