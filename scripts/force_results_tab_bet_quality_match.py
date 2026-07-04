from pathlib import Path
import re

path = Path(r".\src\terminal\tabs\ResultsTab.tsx")
text = path.read_text(encoding="utf-8")

# Add brutally simple same-race horse matcher before export default
insert_after = """function pickInitialRace(rows: Row[]): string {
"""
if "function findBetQualitySameRaceHorse" not in text:
    marker = "export default function ResultsTab"
    helper = r'''
function findBetQualitySameRaceHorse(betRows: Row[], result: Row): Row | undefined {
  const resultTrack = cleanTrack(track(result));
  const resultRaceNo = raceNo(result);
  const resultHorse = cleanHorseLoose(horse(result));

  return betRows.find((row) => {
    if (cleanTrack(track(row)) !== resultTrack) return false;
    if (raceNo(row) !== resultRaceNo) return false;

    const candidates = [
      cleanHorseLoose(horse(row)),
      cleanHorseLoose(row.horse_canon),
      cleanHorseLoose(row.horse_key),
    ];

    return candidates.includes(resultHorse);
  });
}

'''
    text = text.replace(marker, helper + marker)

# Replace bet lookup line/block with forced simple matcher FIRST
text = re.sub(
    r'''const bet\s*=\s*[\s\S]*?;\n\s*const rel =''',
    '''const bet = findBetQualitySameRaceHorse(betRows, result);
      const rel =''',
    text,
    count=1
)

# Make matchedBet count dead simple
text = re.sub(
    r'''const matchedBet = enriched\.filter\(\(row\) => row\.betScore !== null \|\| row\.betGrade !== "—"\)\.length;''',
    '''const matchedBet = enriched.filter((row) => row.betScore !== null).length;''',
    text,
    count=1
)

path.write_text(text, encoding="utf-8")
print("RESULTS_TAB_BET_QUALITY_FORCE_MATCH_COMPLETE")
