from pathlib import Path

path = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = path.read_text(encoding="utf-8")

# ------------------------------------------------------------------
# Fix ChangesSincePanel shape
# ------------------------------------------------------------------

old = '''const changes = raceState.timeline.map((item) => ({
  title: item.title,
  summary: item.summary,
}));'''

new = '''const changes = raceState.timeline.map((item) => ({
  label: item.title,
  value: item.severity,
  detail: item.summary,
}));'''

text = text.replace(old, new)

# ------------------------------------------------------------------
# TEMPORARILY REMOVE RaceStateRail
# We'll replace it with an OperationalStateRail in the next sprint.
# ------------------------------------------------------------------

text = text.replace(
'''          <RaceStateRail raceContext={raceContext} />''',
'''          {/* RaceStateRail temporarily disabled during OS migration */}'''
)

path.write_text(text, encoding="utf-8")

print("[EDGEIQ] COMMAND migration bridge applied")
