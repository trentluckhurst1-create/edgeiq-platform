from pathlib import Path

root = Path.cwd()

service = root / "src/services/buildCommandExecutiveSummary.ts"
service.parent.mkdir(parents=True, exist_ok=True)

service.write_text(r'''export type CommandFindingTone = "info" | "opportunity" | "risk";

export type CommandFinding = {
  label: string;
  text: string;
  tone: CommandFindingTone;
};

export type CommandContender = {
  role: string;
  detail: string;
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
};

export function buildCommandExecutiveSummary(): CommandExecutiveSummary {
  return {
    assessment:
      "EDGEiQ COMMAND converts race shape, market behaviour, confidence, opportunity and risk into a single professional race briefing.",
    findings: [
      {
        label: "Race Shape",
        text: "Tactical setup will be summarised here from existing EDGEiQ intelligence feeds.",
        tone: "info",
      },
      {
        label: "Market Position",
        text: "Overlay, price movement and confidence signals will be surfaced without exposing calculations.",
        tone: "opportunity",
      },
      {
        label: "Risk Profile",
        text: "Primary race risks will be translated into plain professional intelligence.",
        tone: "risk",
      },
    ],
    contenders: [
      {
        role: "Top Intelligence Call",
        detail: "Reserved for selected race leader from existing command summary.",
      },
      {
        role: "Best Overlay",
        detail: "Reserved for value opportunity from current market intelligence.",
      },
      {
        role: "Main Watch",
        detail: "Reserved for key tactical or confidence risk.",
      },
    ],
    market: {
      overlay: "Awaiting race context",
      confidence: "Awaiting race context",
      movement: "Awaiting race context",
    },
  };
}
''', encoding="utf-8")

component = root / "src/components/workspaces/RaceCommandExecutiveWorkspace.tsx"
text = component.read_text(encoding="utf-8")

text = text.replace(
'''import { ReactNode } from "react";''',
'''import { ReactNode } from "react";
import {
  buildCommandExecutiveSummary,
  type CommandExecutiveSummary,
} from "../../services/buildCommandExecutiveSummary";'''
)

start = text.find('type CommandFindingTone = "info" | "opportunity" | "risk";')
end = text.find('type RaceCommandExecutiveWorkspaceProps = {')
if start != -1 and end != -1:
    text = text[:start] + text[end:]

start = text.find('const defaultSummary: CommandExecutiveSummary = {')
end = text.find('export function RaceCommandExecutiveWorkspace')
if start != -1 and end != -1:
    text = text[:start] + text[end:]

text = text.replace(
'''  summary = defaultSummary,''',
'''  summary = buildCommandExecutiveSummary(),'''
)

text = text.replace(
'''

export type { CommandExecutiveSummary };
''',
''
)

component.write_text(text, encoding="utf-8")

print("[EDGEIQ_COMMAND_2D] COMMAND executive summary service extracted")
