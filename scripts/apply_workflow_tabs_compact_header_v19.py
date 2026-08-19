from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_WORKFLOW_TABS_V19.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_WORKFLOW_TABS_V19.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

text = text.replace(
'type WorkbenchMode = "form" | "dna" | "map" | "market" | "evidence" | "notes" | "compare";',
'type WorkbenchMode = "form" | "compare" | "race" | "dna" | "market" | "map" | "notes";'
)

text = text.replace(
'const tabs: WorkbenchMode[] = ["form", "dna", "map", "market", "evidence", "notes"];',
'const tabs: WorkbenchMode[] = ["form", "compare", "race", "dna", "market", "map", "notes"];'
)

text = text.replace(
'{tab === "form" ? "Form Guide" : tab.toUpperCase()}',
'{tab === "form" ? "FORM" : tab === "race" ? "RACE" : tab.toUpperCase()}'
)

text = text.replace(
') : mode === "evidence" ? (\n        <ProfessionalFormTable runs={displayedRuns} />\n      ) : mode === "compare" ? (\n        <CompareWorkspace />',
') : mode === "compare" ? (\n        <CompareWorkspace />\n      ) : mode === "race" ? (\n        <RunnerPlaceholderWorkspace title="Historical Race Book" body="Open the selected historical race as a complete race book with field, result, EPI, ERI, market, map and notes." />'
)

text = text.replace(
'<RunnerPlaceholderWorkspace title="Map" body="Speed map, settling pattern and pace suitability workspace." />',
'<RunnerPlaceholderWorkspace title="Map" body="Speed map, settling pattern and pace suitability workspace." />'
)

tsx.write_text(text, encoding="utf-8")

css_add = r'''

/* EDGEIQ WORKFLOW TABS + COMPACT HEADER — V19 */
.eiq-runner-hero {
  grid-template-columns: 260px minmax(0,1fr) !important;
}

.eiq-runner-hero > div {
  padding: 13px 16px !important;
}

.eiq-runner-hero strong {
  font-size: 20px !important;
  margin-top: 4px !important;
}

.eiq-runner-hero p {
  margin-top: 5px !important;
}

.eiq-runner-hero dl div {
  padding: 12px 12px !important;
}

.eiq-runner-hero dd {
  margin-top: 5px !important;
}

.eiq-runner-summary {
  margin-top: 10px !important;
}

.eiq-runner-summary article {
  padding: 12px 16px !important;
}

.eiq-runner-tabs {
  margin-top: 10px !important;
  padding: 9px 10px !important;
}

.eiq-runner-tabs button {
  height: 30px !important;
  border-radius: 7px !important;
  letter-spacing: .08em !important;
}

.eiq-form-guide-shell {
  margin-top: 10px !important;
}

.eiq-form-guide-toolbar {
  padding: 11px 14px !important;
}

.eiq-form-guide-table th {
  height: 34px !important;
}

.eiq-form-guide-table td {
  height: 38px !important;
}

.eiq-run-detail-v17 {
  padding: 14px !important;
}

.eiq-run-detail-v17__header {
  padding-bottom: 12px !important;
}

.eiq-run-detail-v17__grid {
  margin-top: 12px !important;
}

.eiq-run-detail-v17__grid article {
  min-height: 170px !important;
  padding: 12px !important;
}

.eiq-run-detail-v17__metrics div {
  min-height: 68px !important;
}

.eiq-run-detail-v17__actions {
  margin-top: 12px !important;
  padding-top: 12px !important;
}
'''

if "EDGEIQ WORKFLOW TABS + COMPACT HEADER — V19" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + css_add, encoding="utf-8")

print("[EDGEIQ] Workflow Tabs + Compact Header V19 applied")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
