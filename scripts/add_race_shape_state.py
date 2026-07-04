from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '  const [pacePressureRows, setPacePressureRows] = useState<CsvRow[]>([]);'

new = '''  const [pacePressureRows, setPacePressureRows] = useState<CsvRow[]>([]);
  const [raceShapeRows, setRaceShapeRows] = useState<CsvRow[]>([]);'''

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("ADDED raceShapeRows STATE")
