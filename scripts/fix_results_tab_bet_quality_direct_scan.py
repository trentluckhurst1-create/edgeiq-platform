from pathlib import Path

path = Path(r".\src\terminal\tabs\ResultsTab.tsx")
text = path.read_text(encoding="utf-8")

old = '''      const bet =
        maps.bet.get(key) ??
        maps.bet.get(noDateKey) ??
        maps.bet.get(shortKey) ??
        maps.bet.get(noDateLooseKey) ??
        maps.bet.get(shortLooseKey) ??
        directFind(betRows, result);
'''

new = '''      const bet =
        betRows.find((row) => {
          if (cleanTrack(track(row)) !== cleanTrack(track(result))) return false;
          if (raceNo(row) !== raceNo(result)) return false;

          const resultKeys = [
            cleanHorse(horse(result)),
            cleanHorseLoose(horse(result)),
          ].filter(Boolean);

          const betKeys = [
            cleanHorse(row.horse_key),
            cleanHorse(row.horse_canon),
            cleanHorse(horse(row)),
            cleanHorseLoose(row.horse_key),
            cleanHorseLoose(row.horse_canon),
            cleanHorseLoose(horse(row)),
          ].filter(Boolean);

          return resultKeys.some((k) => betKeys.includes(k));
        }) ??
        maps.bet.get(key) ??
        maps.bet.get(noDateKey) ??
        maps.bet.get(shortKey) ??
        maps.bet.get(noDateLooseKey) ??
        maps.bet.get(shortLooseKey);
'''

if old not in text:
    raise SystemExit("BET_BLOCK_NOT_FOUND")

text = text.replace(old, new)

# Make V8 confidence display human labels too.
text = text.replace(
'''v8Confidence: firstText(v8, ["brc_match_level_v8", "v8_confidence"], "—").replace(/_/g, " "),''',
'''v8Confidence: firstText(v8, ["brc_match_level_v8", "v8_confidence"], "—")
          .replace("TRACK_DISTANCE_RAIL_CONDITION_WIDE", "LOW")
          .replace("TRACK_DISTANCE_RAIL_CONDITION", "MEDIUM")
          .replace("EXACT", "HIGH")
          .replace(/_/g, " "),'''
)

path.write_text(text, encoding="utf-8")
print("BET_QUALITY_DIRECT_SCAN_PATCH_COMPLETE")
