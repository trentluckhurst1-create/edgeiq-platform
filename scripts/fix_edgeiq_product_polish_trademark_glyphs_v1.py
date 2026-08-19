from pathlib import Path
ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
for rel in ["src/edgeiq-os/race/RaceFileV2.tsx", "src/edgeiq-os/race/RaceFileV3.tsx"]:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("™", "")
    path.write_text(text, encoding="utf-8")
print("trademark_glyph_cleanup_done")
