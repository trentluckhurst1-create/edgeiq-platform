from pathlib import Path

targets = [
  Path("src/edgeiq-os/race/RaceFileV3.tsx"),
  Path("src/edgeiq-os/styles/edgeiqOsV2.css"),
]

for path in targets:
    backup = path.with_name(path.stem + "_CHECKPOINT_BEFORE_EDGEIQ_INDEX_FRAMEWORK_V18" + path.suffix)
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
text = tsx.read_text(encoding="utf-8")

repls = {
    "Run Rating™": "EPI™",
    "Race Strength™": "ERI™",
    "Run Rating": "EPI",
    "Race Strength": "ERI",
    "Race Rtg": "ERI",
    "Run Rtg": "EPI",
    "RR": "EPI",
    "RS": "ERI",
    "Assignment Match": "ETI",
    "Evidence Match": "ETI",
    "Overall Match": "ETI",
    "Similarity Engine": "ETI Similarity Engine",
    "EDGEIQ Form Guide": "EDGEiQ Form Guide",
    "Sectional Standard": "ESI Standard",
    "Sectionals in lengths vs EDGEIQ Standard": "ESI in lengths vs EDGEiQ Standard",
    "Negative figures are inside EDGEIQ Standard. Positive figures are outside standard. Raw sectional times are not displayed.": "Negative ESI figures are inside EDGEiQ Standard. Positive ESI figures are outside standard. Raw sectional times are not displayed.",
    "EDGEIQ Evidence Story": "EDGEiQ Evidence Story",
    "EDGEIQ Verdict": "EDGEiQ Verdict",
    "EDGEIQ Run Notes": "EDGEiQ Run Notes",
}

for old, new in repls.items():
    text = text.replace(old, new)

tsx.write_text(text, encoding="utf-8")

css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
css_text = css.read_text(encoding="utf-8")

add = r'''

/* EDGEIQ INDEX FRAMEWORK — V18 */
.eiq-index-framework-note {
  color: rgba(244,248,248,.58);
}

.eiq-form-guide-table th:nth-child(10),
.eiq-form-guide-table th:nth-child(11),
.eiq-form-guide-table th:nth-child(15),
.eiq-form-guide-table td:nth-child(10),
.eiq-form-guide-table td:nth-child(11),
.eiq-form-guide-table td:nth-child(15) {
  color: #f4f8f8 !important;
  font-weight: 900 !important;
}

.eiq-form-guide-table th:nth-child(10),
.eiq-form-guide-table th:nth-child(11),
.eiq-form-guide-table th:nth-child(15) {
  color: #6fa3d8 !important;
}

.eiq-run-detail-v17__metrics small,
.eiq-rating-tile span {
  color: #6fa3d8 !important;
}

.eiq-runner-workspace-v13::before {
  content: "EDGEiQ Index Framework™  ·  EPI Performance  ·  ERI Race Quality  ·  ESI Sectionals  ·  EDI DNA  ·  ETI Transfer";
  display: block;
  margin: 0 0 10px;
  color: rgba(244,248,248,.42);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .14em;
  text-transform: uppercase;
}
'''

if "EDGEIQ INDEX FRAMEWORK — V18" not in css_text:
    css.write_text(css_text + add, encoding="utf-8")

print("[EDGEIQ] Index Framework V18 applied")
print("[EDGEIQ] EPI / ERI / ESI / EDI / ETI labels standardised")
