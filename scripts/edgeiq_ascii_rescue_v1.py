from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8", errors="replace")

safe = []
for ch in text:
    code = ord(ch)
    if code < 128:
        safe.append(ch)
    elif ch in ["—", "–"]:
        safe.append("-")
    elif ch in ["‘", "’"]:
        safe.append("'")
    elif ch in ["“", "”"]:
        safe.append('"')
    elif ch == "…":
        safe.append("...")
    else:
        safe.append("")

text = "".join(safe)

# Clean known damaged UI leftovers
text = text.replace("Open Meeting ", "Open Meeting")
text = text.replace("View Meeting ", "View Meeting")
text = text.replace(" 3 meetings loaded", "3 meetings loaded")
text = text.replace(" -- ", " - ")
text = text.replace(" -  - ", " - ")
text = text.replace("A-Z", "")
text = text.replace("A", "")

path.write_text(text, encoding="utf-8", newline="\n")
print("[ASCII_RESCUE_COMPLETE]")
