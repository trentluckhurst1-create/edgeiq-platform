from pathlib import Path
import re

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

backup = Path(r".\src\App.tsx.backup_before_speedmap_v4_render_fix")
backup.write_text(text, encoding="utf-8")

pattern = r"const currentSpeedRows = useMemo\(\(\) => \{.*?\n\s+\}, \[speedRows, currentRace, silkByHorse\]\);"

new_block = r'''const currentSpeedRows = useMemo(() => {
    if (!currentRace) return [];

    const activeTrack = cleanTrack(currentRace.track);
    const activeRaceNo = currentRace.raceNo;

    const fieldByHorse = new Map<string, CsvRow>();

    currentRace.rows.forEach((row) => {
      const key = compactKey(row.horse);
      if (key) fieldByHorse.set(key, row);
    });

    return speedRows
      .filter((row) => {
        const rowTrack = cleanTrack(row.track ?? row.meeting ?? "");
        const rowRaceNo = num(row.race_no ?? row.raceNumber ?? row.race_no_text ?? row.race ?? "");

        const rowDate = text(row.race_date ?? row.date ?? "");
        const dateOk = !rowDate || rowDate === currentRace.raceDate;

        return (
          dateOk &&
          rowTrack === activeTrack &&
          (rowRaceNo ?? 0) === activeRaceNo
        );
      })
      .map((row) => {
        const fieldRunner =
          fieldByHorse.get(compactKey(row.horse)) ??
          fieldByHorse.get(compactKey(row.horse_name)) ??
          null;

        const displayHorse = text(fieldRunner?.horse ?? row.horse ?? row.horse_name);

        return {
          ...row,
          horse: displayHorse,
          saddlecloth: text(
            fieldRunner?.saddlecloth ??
            fieldRunner?.number ??
            fieldRunner?.tab_no ??
            row.saddlecloth ??
            row.number ??
            row.tab_no
          ),
          jockey: text(fieldRunner?.jockey ?? row.jockey),
          barrier: text(row.barrier ?? fieldRunner?.barrier ?? fieldRunner?.barrier_num),
          silk_url: silkByHorse.get(compactKey(displayHorse)) ?? row.silk_url ?? row.silkUrl ?? "",
          is_scratched: text(fieldRunner?.is_scratched ?? fieldRunner?.scratched ?? row.is_scratched ?? row.scratched ?? ""),
        };
      });
  }, [speedRows, currentRace, silkByHorse]);'''

matches = re.findall(pattern, text, flags=re.S)

if len(matches) != 1:
    print("=" * 80)
    print("FAILED: EXPECTED 1 currentSpeedRows BLOCK, FOUND", len(matches))
    print("=" * 80)
    raise SystemExit(1)

text = re.sub(pattern, new_block, text, count=1, flags=re.S)
path.write_text(text, encoding="utf-8")

print("=" * 80)
print("FIXED currentSpeedRows")
print("V4 rows now match by TRACK + RACE, race_date optional, with runner metadata restored")
print("=" * 80)
