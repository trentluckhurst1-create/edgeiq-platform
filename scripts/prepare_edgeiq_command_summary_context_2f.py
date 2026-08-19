from pathlib import Path

root = Path.cwd()
service = root / "src/services/buildCommandExecutiveSummary.ts"

text = service.read_text(encoding="utf-8")

text = text.replace(
'''export function buildCommandExecutiveSummary(): CommandExecutiveSummary {
  return {''',
'''export function buildCommandExecutiveSummary(): CommandExecutiveSummary {
  const raceContextAvailable = false;

  return {'''
)

text = text.replace(
'''    assessment:
      "EDGEiQ COMMAND converts race shape, market behaviour, confidence, opportunity and risk into a single professional race briefing.",''',
'''    assessment: raceContextAvailable
      ? "EDGEiQ COMMAND has assembled the selected race into an executive intelligence briefing."
      : "Select a race context to activate the full EDGEiQ COMMAND executive briefing.",'''
)

text = text.replace(
'''}''',
'''}''',
1
)

service.write_text(text, encoding="utf-8")
print("[EDGEIQ_COMMAND_2F] command summary prepared for race-context activation")
