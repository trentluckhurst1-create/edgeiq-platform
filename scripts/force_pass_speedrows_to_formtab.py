from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = "selectedCareerStats={selectedCareerStats}`n                  />"
new = "selectedCareerStats={selectedCareerStats}`n                    speedRows={currentSpeedRows}`n                  />"

if old not in text:
    old = "selectedCareerStats={selectedCareerStats}\n                  />"
    new = "selectedCareerStats={selectedCareerStats}\n                    speedRows={currentSpeedRows}\n                  />"

if old not in text:
    raise SystemExit("FORMTAB PROP INSERT POINT NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("FORMTAB NOW RECEIVES currentSpeedRows")
