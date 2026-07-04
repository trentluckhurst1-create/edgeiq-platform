from pathlib import Path
import re

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

# Filter displayRows before grouping so the whole program only sees VIC races.
old = "    return [...grouped.values()].flatMap(rankRows);"
new = '''    return [...grouped.values()]
      .flatMap(rankRows)
      .filter((row) => isVicTrack(row.track));'''

if old not in text:
    raise SystemExit("displayRows return anchor not found")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("FILTERED WHOLE PROGRAM DISPLAY ROWS TO VIC ONLY")
