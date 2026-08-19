from pathlib import Path

app = Path(r".\src\App.tsx")
text = app.read_text(encoding="utf-8")
text = text.replace('tab === "RACE" ? (', 'tab === "INTELLIGENCE" ? (')
app.write_text(text, encoding="utf-8")

overview = Path(r".\src\terminal\tabs\OverviewTab.tsx")
text = overview.read_text(encoding="utf-8")
text = text.replace(
  'setTab: (value: "OVERVIEW" | "RACE" | "MARKET" | "RESULTS" | "INTELLIGENCE") => void;',
  'setTab: (value: "OVERVIEW" | "INTELLIGENCE" | "MARKET" | "RESULTS" | "LEARNING") => void;'
)
text = text.replace('setTab("RACE");', 'setTab("INTELLIGENCE");')
overview.write_text(text, encoding="utf-8")

print("REMAINING NAV RACE REFERENCES FIXED")
