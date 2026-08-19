from pathlib import Path

path = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'import { getCommandRaceContext } from "../services/race-context";',
'import { getOperationalRaceState } from "../services/intelligence-orchestrator";'
)

start = text.find("const raceContext =")
end = text.find("export function EdgeiqCommandWorkspace()")

replacement = r'''
const raceState = getOperationalRaceState();

const liveStatus = raceState.feedHealth.map((feed) => ({
  label: feed.label,
  value: feed.status,
  tone:
    feed.status === "READY"
      ? "good"
      : feed.status === "PARTIAL"
      ? "info"
      : "neutral",
}));

const evidence = raceState.evidence.map((item) => item.title);

'''

text = text[:start] + replacement + text[end:]

text = text.replace(
"raceContext.raceLabel",
"raceState.raceName"
)

text = text.replace(
"raceContext.distance",
"raceState.distance"
)

text = text.replace(
"raceContext.className",
"raceState.raceClass"
)

text = text.replace(
"raceContext.trackCondition",
"raceState.trackCondition"
)

text = text.replace(
"raceContext.railPosition",
"raceState.rail"
)

text = text.replace(
"raceContext.updatedAt",
'"LIVE"'
)

text = text.replace(
"{situation.map((line) => <p key={line}>{line}</p>)}",
"<p>{raceState.currentSituation}</p>"
)

text = text.replace(
"""{matters.map((item) => <li key={item}>{item}</li>)}""",
"<li>{raceState.whyItMatters}</li>"
)

text = text.replace(
"currentAssessment.marketPrice",
'"LIVE"'
)

text = text.replace(
"currentAssessment.supportingIntelligence",
"`${raceState.evidence.length} evidence sources`"
)

text = text.replace(
"{marketRelationship}",
"{raceState.marketRelationship}"
)

path.write_text(text,encoding="utf-8")

print("[EDGEIQ] COMMAND workspace migrated to OperationalRaceState")
