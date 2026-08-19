from pathlib import Path

root = Path.cwd()
router = root / "src/components/workspaces/EdgeiqWorkspaceRouter.tsx"

text = router.read_text(encoding="utf-8")

text = text.replace(
'''  const { activeSection, activeWorkspace } = useEdgeiqOs();
  const commandSummary = buildCommandExecutiveSummary();''',
'''  const { activeSection, activeWorkspace } = useEdgeiqOs();
  const commandSummary = buildCommandExecutiveSummary({
    meeting: "Current Meeting",
    race: "Selected Race",
    distance: "Race Distance",
    track: "Track Condition",
    rail: "Rail Position",
    jump: "Jump Countdown",
  });'''
)

router.write_text(text, encoding="utf-8")
print("[EDGEIQ_COMMAND_2H] temporary race context passed into COMMAND summary")
