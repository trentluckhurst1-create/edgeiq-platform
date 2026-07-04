from pathlib import Path
import re

path = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard\src\components\RaceIntelligenceScreen.tsx")
backup = path.with_name("RaceIntelligenceScreen_CHECKPOINT_FORM_ROW_MERGE_FIX_20260628.tsx")
text = path.read_text(encoding="utf-8")
backup.write_text(text, encoding="utf-8")

# Insert form row map helper before enriched useMemo
marker = "  const enriched = useMemo(() => {"
helper = r'''
  const formEnrichmentByRunnerKey = useMemo(() => {
    const map = new Map<string, Row>();
    formEnrichmentRows.forEach((formRow) => {
      const key =
        firstText(formRow, ["runner_key"], "") ||
        [
          firstText(formRow, ["race_date"], ""),
          cleanTrack(firstText(formRow, ["track"], "")),
          `R${firstText(formRow, ["race_no"], "").replace(/^R/i, "")}`,
          cleanHorseLoose(firstText(formRow, ["horse_key"], "")) || cleanHorseLoose(firstText(formRow, ["horse"], "")),
        ].join("_");
      if (key) map.set(key, formRow);
    });
    return map;
  }, [formEnrichmentRows]);

'''
if "const formEnrichmentByRunnerKey = useMemo" not in text:
    text = text.replace(marker, helper + marker)

# Replace current form lookup with map-based fallback.
old = '      const formEnrichment = findFormEnrichmentSidecar(formEnrichmentRows, row);'
new = r'''      const formLookupKey =
        firstText(row, ["runner_key"], "") ||
        [
          firstText(row, ["race_date"], ""),
          cleanTrack(firstText(row, ["track"], "")),
          `R${firstText(row, ["race_no"], "").replace(/^R/i, "")}`,
          cleanHorseLoose(firstText(row, ["horse_key"], "")) || cleanHorseLoose(firstText(row, ["horse"], "")),
        ].join("_");
      const formEnrichment =
        formEnrichmentByRunnerKey.get(formLookupKey) ||
        findFormEnrichmentSidecar(formEnrichmentRows, row);'''
text = text.replace(old, new)

# Add dependency.
text = text.replace(
    'formEnrichmentRows]);',
    'formEnrichmentRows, formEnrichmentByRunnerKey]);'
)

# Make selectedRunnerForm use merged row fallback too.
text = text.replace(
    'const selectedRunnerForm = selected?.formEnrichment || {};',
    'const selectedRunnerForm = selected?.formEnrichment || selected?.row || {};'
)

path.write_text(text, encoding="utf-8")
print("[FORM_ROW_MERGE_FIX] COMPLETE")
print(backup)
