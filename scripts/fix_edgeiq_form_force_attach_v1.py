from pathlib import Path
import re

path = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard\src\components\RaceIntelligenceScreen.tsx")
backup = path.with_name("RaceIntelligenceScreen_CHECKPOINT_FORM_FORCE_ATTACH_20260628.tsx")
text = path.read_text(encoding="utf-8")
backup.write_text(text, encoding="utf-8")

# Remove the red temporary debug block.
text = re.sub(
    r'\n\s*<div style=\{\{ border: "1px solid rgba\(248,113,113,\.65\)"[\s\S]*?</div>\s*\n\s*<div style=\{selectedGridStyle\(8\)\}>',
    '\n                    <div style={selectedGridStyle(8)}>',
    text,
    count=1
)

# Build a simple direct form map inside enriched useMemo if not already present.
if "const formDirectMap = new Map<string, Row>();" not in text:
    text = text.replace(
        "  const enriched = useMemo(() => {\n",
        '''  const enriched = useMemo(() => {
    const formDirectMap = new Map<string, Row>();
    formEnrichmentRows.forEach((formRow) => {
      const directKey = [
        firstText(formRow, ["race_date"], ""),
        cleanTrack(firstText(formRow, ["track"], "")),
        String(firstText(formRow, ["race_no"], "")).replace(/^R/i, ""),
        cleanHorseLoose(firstText(formRow, ["horse_key"], "")) || cleanHorseLoose(firstText(formRow, ["horse"], "")),
      ].join("|");
      formDirectMap.set(directKey, formRow);
    });

'''
    )

# Replace the messy form lookup with deterministic direct key lookup.
pattern = re.compile(
    r'\s*const formLookupKey =[\s\S]*?findFormEnrichmentSidecar\(formEnrichmentRows, row\);',
    re.M
)

replacement = r'''
      const formDirectKey = [
        firstText(row, ["race_date"], ""),
        cleanTrack(firstText(row, ["track"], "")),
        String(firstText(row, ["race_no"], "")).replace(/^R/i, ""),
        cleanHorseLoose(firstText(row, ["horse_key"], "")) || cleanHorseLoose(firstText(row, ["horse"], "")),
      ].join("|");
      const formEnrichment =
        formDirectMap.get(formDirectKey) ||
        findFormEnrichmentSidecar(formEnrichmentRows, row);'''

text, count = pattern.subn(replacement, text, count=1)
if count == 0:
    text = text.replace(
        "      const formEnrichment = findFormEnrichmentSidecar(formEnrichmentRows, row);",
        replacement
    )

# selectedRunnerForm must use attached form only, then row fallback.
text = text.replace(
    "const selectedRunnerForm = selected?.formEnrichment || selected?.row || {};",
    "const selectedRunnerForm = selected?.formEnrichment || selected?.row || {};"
)

path.write_text(text, encoding="utf-8")
print("[FORM_FORCE_ATTACH] COMPLETE")
print(backup)
