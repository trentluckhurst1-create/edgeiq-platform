from pathlib import Path

root = Path.cwd()
shell = root / "src/components/shell/EdgeiqOsShell.tsx"

text = shell.read_text(encoding="utf-8")

text = text.replace(
'''  const nextTheme = useMemo(() => (theme === "dark" ? "light" : "dark"), [theme]);
  const os = useEdgeiqOs();''',
'''  const nextTheme = useMemo(() => (theme === "dark" ? "light" : "dark"), [theme]);
  const os = useEdgeiqOs();
  const toolbarContext = os.raceContext;'''
)

text = text.replace("<strong>{meetingName}</strong>", "<strong>{toolbarContext.meeting || meetingName}</strong>")
text = text.replace("<strong>{raceLabel}</strong>", "<strong>{toolbarContext.race || raceLabel}</strong>")
text = text.replace("<strong>{distanceLabel}</strong>", "<strong>{toolbarContext.distance || distanceLabel}</strong>")
text = text.replace("<strong>{trackLabel}</strong>", "<strong>{toolbarContext.track || trackLabel}</strong>")
text = text.replace("<strong>{railLabel}</strong>", "<strong>{toolbarContext.rail || railLabel}</strong>")

shell.write_text(text, encoding="utf-8")
print("[EDGEIQ_OS_TOOLBAR_CONTEXT] toolbar now reads OS race context")
