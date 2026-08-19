from pathlib import Path
import re

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

replacements = {
r'''function fairPrice\(row: CsvRow\): number \{
[\s\S]*?\n\}''':
'''function fairPrice(row: CsvRow): number {
  return firstNumber(row, ["ratedPrice"], 0);
}''',

r'''function probability\(row: CsvRow\): number \{
[\s\S]*?\n\}''':
'''function probability(row: CsvRow): number {
  const direct = firstNumber(row, ["probability", "winProbability"], 0);
  if (direct > 0) return direct > 1 ? direct / 100 : direct;

  const fair = fairPrice(row);
  return fair > 0 ? 1 / fair : 0;
}''',

r'''function livePrice\(row: CsvRow\): number \{
[\s\S]*?\n\}''':
'''function livePrice(row: CsvRow): number {
  return firstNumber(row, ["marketPrice"], 0);
}''',

r'''function overlay\(row: CsvRow\): number \{
[\s\S]*?\n\}''':
'''function overlay(row: CsvRow): number {
  return firstNumber(row, ["edgePct"], 0);
}''',

r'''function decision\(row: CsvRow\): string \{
[\s\S]*?\n\}''':
'''function decision(row: CsvRow): string {
  const live = livePrice(row);
  const fair = fairPrice(row);
  const edge = overlay(row);
  const grade = betGrade(row).toUpperCase();

  if (live <= 0) return "NO MARKET";
  if (fair <= 0) return "NO PRICE";
  if (["A+", "A"].includes(grade) && edge > 0) return "PRIORITY";
  if (grade === "B" && edge > 0) return "VALUE WATCH";
  if (edge >= 18) return "WATCH";
  if (edge >= 6) return "LEAN";
  if (edge <= -20) return "AVOID";
  return "NEUTRAL";
}'''
}

for pattern, repl in replacements.items():
    text, count = re.subn(pattern, repl, text, count=1)
    if count != 1:
        raise SystemExit(f"FAILED_REWRITE_PATTERN: {pattern[:80]}")

path.write_text(text, encoding="utf-8")
print("[RACE_INTELLIGENCE_PRICING_SOURCE_REWRITE] COMPLETE")
