from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

anchor = '''  const currentPacePressureRows = useMemo(() => {
    if (!currentRace) return [];
    return pacePressureRows.filter((row) =>
      text(row.race_date) === currentRace.raceDate &&
      cleanTrack(row.track) === cleanTrack(currentRace.track) &&
      (num(row.race_no) ?? 0) === currentRace.raceNo
    );
  }, [pacePressureRows, currentRace]);
'''

insert = '''

  const currentRaceShapeRow = useMemo(() => {
    if (!currentRace) return null;

    return (
      raceShapeRows.find(
        (row) =>
          text(row.race_date) === currentRace.raceDate &&
          cleanTrack(row.track) === cleanTrack(currentRace.track) &&
          (num(row.race_no) ?? 0) === currentRace.raceNo
      ) ?? null
    );
  }, [raceShapeRows, currentRace]);

'''

text = text.replace(anchor, anchor + insert)

path.write_text(text, encoding="utf-8")

print("ADDED currentRaceShapeRow")
