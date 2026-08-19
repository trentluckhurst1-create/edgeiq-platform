from pathlib import Path

root = Path.cwd()

path = root / "src/components/workspaces/RaceCommandExecutiveWorkspace.tsx"
text = path.read_text(encoding="utf-8")

text = text.replace(
'''type RaceCommandExecutiveWorkspaceProps = {
  legacyCommand?: ReactNode;
};''',
'''type CommandFindingTone = "info" | "opportunity" | "risk";

type CommandFinding = {
  label: string;
  text: string;
  tone: CommandFindingTone;
};

type CommandContender = {
  role: string;
  detail: string;
};

type CommandExecutiveSummary = {
  assessment: string;
  findings: CommandFinding[];
  contenders: CommandContender[];
  market: {
    overlay: string;
    confidence: string;
    movement: string;
  };
};

type RaceCommandExecutiveWorkspaceProps = {
  legacyCommand?: ReactNode;
  summary?: CommandExecutiveSummary;
};'''
)

text = text.replace(
'''const executiveFindings = [
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
];

const primaryContenders = [
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
];''',
'''const defaultSummary: CommandExecutiveSummary = {
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
};'''
)

text = text.replace(
'''export function RaceCommandExecutiveWorkspace({ legacyCommand }: RaceCommandExecutiveWorkspaceProps) {''',
'''export function RaceCommandExecutiveWorkspace({
  legacyCommand,
  summary = defaultSummary,
}: RaceCommandExecutiveWorkspaceProps) {'''
)

text = text.replace(
'''        <div className="edgeiq-command-executive__assessment-text">
          EDGEiQ COMMAND converts race shape, market behaviour, confidence, opportunity and risk into a single
          professional race briefing.
        </div>''',
'''        <div className="edgeiq-command-executive__assessment-text">{summary.assessment}</div>'''
)

text = text.replace("executiveFindings.map", "summary.findings.map")
text = text.replace("primaryContenders.map", "summary.contenders.map")

text = text.replace(
'''            <strong>Awaiting race context</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Confidence</span>
            <strong>Awaiting race context</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Movement</span>
            <strong>Awaiting race context</strong>''',
'''            <strong>{summary.market.overlay}</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Confidence</span>
            <strong>{summary.market.confidence}</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Movement</span>
            <strong>{summary.market.movement}</strong>'''
)

if "export type { CommandExecutiveSummary };" not in text:
    text += "\nexport type { CommandExecutiveSummary };\n"

path.write_text(text, encoding="utf-8")
print("[EDGEIQ_COMMAND_2C] typed presentation summary added")
