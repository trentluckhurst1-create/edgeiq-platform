from pathlib import Path

root = Path.cwd()
store = root / "src/state/edgeiqOsStore.tsx"

text = store.read_text(encoding="utf-8")

text = text.replace(
'''type EdgeiqOsState = {
  activeSection: EdgeiqSection;
  activeWorkspace: EdgeiqWorkspace;''',
'''type EdgeiqRaceContext = {
  meeting: string;
  race: string;
  distance: string;
  track: string;
  rail: string;
  jump: string;
};

type EdgeiqOsState = {
  activeSection: EdgeiqSection;
  activeWorkspace: EdgeiqWorkspace;
  raceContext: EdgeiqRaceContext;'''
)

text = text.replace(
'''  const [activeWorkspace, setActiveWorkspace] = useState<EdgeiqWorkspace>(readStoredWorkspace);''',
'''  const [activeWorkspace, setActiveWorkspace] = useState<EdgeiqWorkspace>(readStoredWorkspace);

  const raceContext: EdgeiqRaceContext = {
    meeting: "Current Meeting",
    race: "Selected Race",
    distance: "Race Distance",
    track: "Track Condition",
    rail: "Rail Position",
    jump: "Jump Countdown",
  };'''
)

text = text.replace(
'''      activeWorkspace,
      setActiveSection,''',
'''      activeWorkspace,
      raceContext,
      setActiveSection,'''
)

if "export type { EdgeiqRaceContext };" not in text:
    text += "\nexport type { EdgeiqRaceContext };\n"

store.write_text(text, encoding="utf-8")

router = root / "src/components/workspaces/EdgeiqWorkspaceRouter.tsx"
text = router.read_text(encoding="utf-8")

text = text.replace(
'''  const { activeSection, activeWorkspace } = useEdgeiqOs();
  const commandSummary = buildCommandExecutiveSummary({
    meeting: "Current Meeting",
    race: "Selected Race",
    distance: "Race Distance",
    track: "Track Condition",
    rail: "Rail Position",
    jump: "Jump Countdown",
  });''',
'''  const { activeSection, activeWorkspace, raceContext } = useEdgeiqOs();
  const commandSummary = buildCommandExecutiveSummary(raceContext);'''
)

router.write_text(text, encoding="utf-8")
print("[EDGEIQ_OS_RACE_CONTEXT_STORE] race context moved into OS store")
