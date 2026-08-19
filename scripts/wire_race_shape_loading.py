from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''          pacePressure,
          sectionalTempo,'''

new = '''          pacePressure,
          raceShape,
          sectionalTempo,'''

text = text.replace(old, new)

old2 = '''        setPacePressureRows(pacePressure);
        setSectionalTempoRows(sectionalTempo);'''

new2 = '''        setPacePressureRows(pacePressure);
        setRaceShapeRows(raceShape);
        setSectionalTempoRows(sectionalTempo);'''

text = text.replace(old2, new2)

path.write_text(text, encoding="utf-8")

print("WIRED raceShapeRows LOADING")
