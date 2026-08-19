from pathlib import Path

root = Path.cwd()
service = root / "src/services/buildCommandExecutiveSummary.ts"

text = service.read_text(encoding="utf-8")

text = text.replace(
'''export type CommandExecutiveSummary = {''',
'''export type CommandRaceContext = {
  meeting?: string;
  race?: string;
  distance?: string;
  track?: string;
  rail?: string;
  jump?: string;
};

export type CommandExecutiveSummary = {'''
)

text = text.replace(
'''export function buildCommandExecutiveSummary(): CommandExecutiveSummary {
  const raceContextAvailable = false;''',
'''export function buildCommandExecutiveSummary(raceContext?: CommandRaceContext): CommandExecutiveSummary {
  const raceContextAvailable = Boolean(raceContext?.meeting || raceContext?.race);'''
)

text = text.replace(
'''      ? "EDGEiQ COMMAND has assembled the selected race into an executive intelligence briefing."''',
'''      ? `EDGEiQ COMMAND has assembled ${raceContext?.meeting ?? "the selected meeting"} ${raceContext?.race ?? "race"} into an executive intelligence briefing.`'''
)

service.write_text(text, encoding="utf-8")
print("[EDGEIQ_COMMAND_2G] race context contract added")
