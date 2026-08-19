from pathlib import Path
ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
files = [
    ROOT / "src/edgeiq-os/race/RaceFileV2.tsx",
    ROOT / "src/edgeiq-os/race/RaceFileV3.tsx",
]
for path in files:
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    replacements = {
        "Â·": " | ",
        "â„¢": "",
        "Î”": "Delta",
        "â€”": "-",
        "â€™": "'",
        "â†’": "->",
        "ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢": "",
        "Ã¢â€žÂ¢": "",
        "Ãƒâ€šÃ‚Â·": " | ",
        "Ã‚Â·": " | ",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬": "-",
        "Ã¢â€ â€™": "->",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace('return "-";', 'return "-";')
    text = text.replace('raw === "-"', 'raw === "-"')
    text = text.replace('<th>Race Strength</th>', '<th>Race Strength</th>')
    path.write_text(text, encoding="utf-8")
print("encoding_cleanup_done")
