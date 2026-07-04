from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

needle = '''  const surfaceLabel = staleSnapshot ? "EDGEIQ RACING - HISTORICAL SNAPSHOT" : "EDGEIQ RACING - LIVE INTELLIGENCE";

  return (
'''

insert = '''  const surfaceLabel = staleSnapshot ? "EDGEIQ RACING - HISTORICAL SNAPSHOT" : "EDGEIQ RACING - LIVE INTELLIGENCE";

  const currentRaceHeaderMeta = currentRace ? activeRaceMeta(currentRace.track, currentRace.raceNo, currentRace.raceDate) : undefined;
  const currentRaceHeaderTime = currentRace
    ? displayUserLocalRaceTime(
        {
          ...(currentRace.rows[0] ?? {}),
          race_time:
            text(currentRace.rows[0]?.raceTime) ||
            text(currentRace.raceTime) ||
            text(currentRaceHeaderMeta?.race_time) ||
            text(currentRaceHeaderMeta?.jump_time),
          jump_time:
            text(currentRaceHeaderMeta?.jump_time) ||
            text(currentRaceHeaderMeta?.race_time) ||
            text(currentRace.rows[0]?.raceTime) ||
            text(currentRace.raceTime),
          race_datetime:
            text(currentRaceHeaderMeta?.race_datetime) ||
            text(currentRaceHeaderMeta?.race_time),
        },
        currentRace
      )
    : "TIME TBC";

  return (
'''

if needle not in text:
    raise SystemExit("SURFACE_LABEL_BLOCK_NOT_FOUND")

text = text.replace(needle, insert)

text = text.replace(
'''                <span>{displayUserLocalRaceTime(currentRace.rows[0], currentRace)}</span>''',
'''                <span>{currentRaceHeaderTime}</span>'''
)

path.write_text(text, encoding="utf-8")
print("APP_HEADER_TIME_FIXED")
