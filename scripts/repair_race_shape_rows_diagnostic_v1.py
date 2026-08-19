from pathlib import Path

path = Path("src/edgeiq-os/services/adapters/RaceShapeAdapter.ts")
text = path.read_text(encoding="utf-8")

text = text.replace(
"    const row = snapshot.raceShape[0];",
"    const rows = snapshot.raceShape;\n    const row = rows[0];"
)

path.write_text(text, encoding="utf-8")

print("[EDGEIQ] RaceShape rows variable repaired")
