from pathlib import Path

path = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard\src\components\RaceIntelligenceScreen.tsx")
backup = path.with_name("RaceIntelligenceScreen_CHECKPOINT_FORM_V2_EXCLUSIVE_FIX_20260628.tsx")
text = path.read_text(encoding="utf-8")
backup.write_text(text, encoding="utf-8")

# 1. Add robust form sidecar finder after command sidecar finder.
marker = '''function findCommandEnrichmentSidecar(rows: Row[], base: Row): Row | undefined {
  const baseDate = raceDate(base);
  const baseTrack = cleanTrack(track(base));'''

insert_before = marker

helper = r'''
function findFormEnrichmentSidecar(rows: Row[], base: Row): Row | undefined {
  const baseDate = raceDate(base);
  const baseTrack = cleanTrack(track(base));
  const baseRace = raceNo(base);
  const baseHorse = cleanHorse(horse(base));
  const baseHorseLoose = cleanHorseLoose(firstText(base, ["horse_key"], "")) || cleanHorseLoose(horse(base));

  return rows.find((row) => {
    const dateOk = !baseDate || !raceDate(row) || raceDate(row) === baseDate;
    const trackOk = cleanTrack(track(row)) === baseTrack;
    const raceOk = raceNo(row) === baseRace;
    const horseOk =
      cleanHorse(horse(row)) === baseHorse ||
      cleanHorseLoose(firstText(row, ["horse_key"], "")) === baseHorseLoose ||
      cleanHorseLoose(horse(row)) === baseHorseLoose;
    return dateOk && trackOk && raceOk && horseOk;
  });
}

'''

if "function findFormEnrichmentSidecar" not in text:
    text = text.replace(insert_before, helper + insert_before)

# 2. Use robust finder instead of generic finder.
text = text.replace(
    'const formEnrichment = findSidecarByRaceHorse(formEnrichmentRows, row);',
    'const formEnrichment = findFormEnrichmentSidecar(formEnrichmentRows, row);'
)

# 3. Make selectedRunnerForm V2 exclusive.
text = text.replace(
    'const selectedRunnerForm = selected?.formEnrichment || selected?.formIntelligence || selected?.runnerForm;',
    'const selectedRunnerForm = selected?.formEnrichment || {};'
)

# 4. Make FORM runner list V2 exclusive.
text = text.replace(
    'const itemForm = item.formEnrichment || item.formIntelligence || item.runnerForm;',
    'const itemForm = item.formEnrichment || {};'
)

# 5. Fix legacy global rating fallbacks to include V2 field names first.
text = text.replace(
    'firstNum(selectedRunnerForm, ["last_start_rating", "rating_1"])',
    'firstNum(selectedRunnerForm, ["form_last_start_rating", "last_start_rating", "rating_1"])'
)
text = text.replace(
    'firstNum(selectedRunnerForm, ["avg_rating_last5"])',
    'firstNum(selectedRunnerForm, ["form_avg_rating_last5", "avg_rating_last5"])'
)
text = text.replace(
    'firstNum(selectedRunnerForm, ["best_rating_last5", "peak_rating"])',
    'firstNum(selectedRunnerForm, ["form_peak_rating_last5", "best_rating_last5", "peak_rating"])'
)

path.write_text(text, encoding="utf-8")
print("[FORM_V2_EXCLUSIVE_FIX] COMPLETE")
print(backup)
