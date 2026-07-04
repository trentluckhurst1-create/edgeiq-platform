from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = 'paceRows={currentPacePressureRows}'

new = 'paceRows={currentPacePressureRows} raceShape={currentRaceShapeRow}'

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("PASSED raceShape INTO SpeedMapTab")
