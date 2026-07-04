from pathlib import Path

path = Path(r".\src\terminal\layout\terminalTabs.ts")
text = path.read_text(encoding="utf-8")

text = text.replace('"RACE"', '"INTELLIGENCE"')
text = text.replace('"INTELLIGENCE"', '"LEARNING"', 1) if '["OVERVIEW", "INTELLIGENCE", "MARKET", "RESULTS", "INTELLIGENCE"]' in text else text

# Safer full replacement for the likely file shape
text = text.replace(
'''export const EDGEIQ_TABS = [
  "OVERVIEW",
  "RACE",
  "MARKET",
  "RESULTS",
  "LEARNING",
] as const;''',
'''export const EDGEIQ_TABS = [
  "OVERVIEW",
  "INTELLIGENCE",
  "MARKET",
  "RESULTS",
  "LEARNING",
] as const;'''
)

text = text.replace(
'''export type EdgeTabKey =
  | "OVERVIEW"
  | "RACE"
  | "MARKET"
  | "RESULTS"
  | "LEARNING";''',
'''export type EdgeTabKey =
  | "OVERVIEW"
  | "INTELLIGENCE"
  | "MARKET"
  | "RESULTS"
  | "LEARNING";'''
)

path.write_text(text, encoding="utf-8")
print("TERMINAL TABS UPDATED")
