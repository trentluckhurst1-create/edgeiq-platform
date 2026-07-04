from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''const TAB_KEYS: TabKey[] = [
  "OVERVIEW",
  "RACE",
  "MARKET",
  "RESULTS",
  "INTELLIGENCE",
];''',
'''const TAB_KEYS: TabKey[] = [
  "OVERVIEW",
  "INTELLIGENCE",
  "MARKET",
  "RESULTS",
  "LEARNING",
];'''
)

text = text.replace(
'''type TabKey =
  | "OVERVIEW"
  | "RACE"
  | "MARKET"
  | "RESULTS"
  | "INTELLIGENCE";''',
'''type TabKey =
  | "OVERVIEW"
  | "INTELLIGENCE"
  | "MARKET"
  | "RESULTS"
  | "LEARNING";'''
)

text = text.replace(
'''if (typeof window === "undefined") return "RACE";''',
'''if (typeof window === "undefined") return "INTELLIGENCE";'''
)

text = text.replace(
'''return saved && TAB_KEYS.includes(saved) ? saved : "RACE";''',
'''return saved && TAB_KEYS.includes(saved) ? saved : "INTELLIGENCE";'''
)

text = text.replace(
'''OVERVIEW: "MISSION CONTROL",
    RACE: "RACE DECISION WORKSPACE",
    MARKET: "LIVE MARKET INTELLIGENCE",
    RESULTS: "SETTLEMENT / RESULTS",
    INTELLIGENCE: "MARKET / MODEL INTELLIGENCE",''',
'''OVERVIEW: "MISSION CONTROL",
    INTELLIGENCE: "RACE INTELLIGENCE WORKSPACE",
    MARKET: "LIVE MARKET INTELLIGENCE",
    RESULTS: "SETTLEMENT / RESULTS",
    LEARNING: "MARKET / MODEL INTELLIGENCE",'''
)

text = text.replace(
''') : tab === "RACE" ? (
            <RaceIntelligenceScreen''',
''') : tab === "INTELLIGENCE" ? (
            <RaceIntelligenceScreen'''
)

text = text.replace(
''') : tab === "INTELLIGENCE" ? (
            <LearningTab />''',
''') : tab === "LEARNING" ? (
            <LearningTab />'''
)

path.write_text(text, encoding="utf-8")
print("TAB RENAME COMPLETE")
