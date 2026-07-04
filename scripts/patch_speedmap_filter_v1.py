from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")

text = path.read_text(encoding="utf-8")

old = """const raceRows = rows.filter(
    (r) =>
      String(r.track || "") === String(track || "") &&
      String(r.race_no || "") === String(raceNo || "")
  );"""

new = """const raceRows = rows.filter((r) => {
    const rowTrack = String(
      r.track || r.meeting || ""
    ).trim().toUpperCase();

    const activeTrack = String(
      track || ""
    ).trim().toUpperCase();

    const rowRace = String(
      r.race_no || r.raceNumber || ""
    ).replace(/[^0-9]/g, "");

    const activeRace = String(
      raceNo || ""
    ).replace(/[^0-9]/g, "");

    return (
      rowTrack === activeTrack &&
      rowRace === activeRace
    );
  });"""

if old not in text:
    raise Exception("FILTER BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("SPEED MAP FILTER PATCHED")
print("=" * 80)
