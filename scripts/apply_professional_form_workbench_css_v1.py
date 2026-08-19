from pathlib import Path

path = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_FORM_WORKBENCH_CSS_20260709.css")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

css = r'''

/* EDGEIQ FORM DESK — PROFESSIONAL WORKBENCH V1 */
.eiq-form-workbench {
  display: grid;
  gap: 18px;
  padding: 22px;
  color: #f4f8f8;
}

.eiq-form-workbench__header,
.eiq-horse-workbench-header,
.eiq-analyst-summary,
.eiq-form-toolbar,
.eiq-professional-form-table,
.eiq-run-report {
  border: 1px solid rgba(90,255,220,.10);
  background: rgba(3,8,10,.62);
  box-shadow: 0 18px 50px rgba(0,0,0,.22);
}

.eiq-form-workbench__header {
  display: grid;
  grid-template-columns: minmax(0,1fr) 360px;
  gap: 24px;
  padding: 22px 26px;
  border-radius: 10px;
}

.eiq-form-workbench span,
.eiq-form-toolbar span,
.eiq-run-report span {
  display: block;
  color: #43efc6;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.eiq-form-workbench strong {
  color: #f4f8f8;
}

.eiq-form-workbench__header strong {
  display: block;
  margin-top: 8px;
  font-size: 26px;
  font-weight: 500;
}

.eiq-form-workbench__header p,
.eiq-horse-workbench-header p,
.eiq-analyst-summary p,
.eiq-run-report p {
  margin: 7px 0 0;
  color: rgba(244,248,248,.68);
  font-size: 13px;
  line-height: 1.45;
}

.eiq-horse-workbench-header {
  display: grid;
  grid-template-columns: 360px minmax(0,1fr);
  gap: 18px;
  padding: 20px;
  border-radius: 10px;
}

.eiq-horse-workbench-header > div:first-child strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  font-weight: 600;
}

.eiq-horse-workbench-metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(0,1fr));
  gap: 10px;
}

.eiq-workbench-metric {
  min-height: 72px;
  padding: 13px 14px;
  border: 1px solid rgba(90,255,220,.08);
  background: rgba(255,255,255,.025);
}

.eiq-workbench-metric strong {
  display: block;
  margin-top: 8px;
  font-size: 14px;
  font-weight: 700;
}

.eiq-analyst-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0,1fr));
  gap: 0;
  border-radius: 10px;
  overflow: hidden;
}

.eiq-analyst-summary article {
  min-height: 118px;
  padding: 18px 20px;
  border-right: 1px solid rgba(90,255,220,.08);
}

.eiq-analyst-summary article:last-child {
  border-right: 0;
}

.eiq-analyst-summary strong {
  display: block;
  margin-top: 10px;
  font-size: 16px;
  line-height: 1.35;
}

.eiq-form-toolbar {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  align-items: center;
  gap: 18px;
  padding: 14px 18px;
  border-radius: 10px;
}

.eiq-form-toolbar strong {
  display: block;
  margin-top: 5px;
  font-size: 14px;
}

.eiq-form-toolbar nav {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.eiq-form-toolbar button {
  height: 32px;
  padding: 0 13px;
  border: 1px solid rgba(90,255,220,.14);
  border-radius: 999px;
  background: rgba(12,22,30,.85);
  color: rgba(244,248,248,.82);
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.eiq-form-toolbar button.is-active,
.eiq-form-toolbar button:hover {
  border-color: rgba(67,239,198,.55);
  color: #43efc6;
  background: rgba(67,239,198,.08);
}

.eiq-professional-form-table {
  overflow: auto;
  border-radius: 10px;
}

.eiq-professional-form-table table {
  width: 100%;
  min-width: 1320px;
  border-collapse: collapse;
  font-size: 12px;
}

.eiq-professional-form-table th {
  position: sticky;
  top: 0;
  z-index: 2;
  height: 38px;
  padding: 0 10px;
  border-bottom: 1px solid rgba(90,255,220,.14);
  background: #05090d;
  color: rgba(244,248,248,.62);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .12em;
  text-align: left;
  text-transform: uppercase;
  white-space: nowrap;
}

.eiq-professional-form-table td {
  height: 40px;
  padding: 0 10px;
  border-bottom: 1px solid rgba(90,255,220,.07);
  color: rgba(244,248,248,.82);
  white-space: nowrap;
}

.eiq-professional-form-table tbody tr {
  cursor: pointer;
}

.eiq-professional-form-table tbody tr:hover td,
.eiq-professional-form-table tbody tr.is-open td {
  background: rgba(67,239,198,.055);
}

.eiq-professional-form-table td strong {
  font-weight: 800;
}

.eiq-professional-form-table td b {
  display: block;
  color: #43efc6;
  font-size: 12px;
}

.eiq-professional-form-table td em {
  display: block;
  margin-top: 2px;
  color: rgba(244,248,248,.58);
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
  letter-spacing: .04em;
  text-transform: uppercase;
}

.eiq-form-report-row td {
  height: auto;
  padding: 0 !important;
  background: rgba(0,0,0,.22);
}

.eiq-run-report {
  margin: 0;
  padding: 18px;
  border-left: 3px solid rgba(67,239,198,.55);
  border-right: 0;
  border-top: 0;
  border-bottom: 1px solid rgba(90,255,220,.09);
  box-shadow: none;
}

.eiq-run-report__grid {
  display: grid;
  grid-template-columns: 1fr 1.15fr 1fr;
  gap: 14px;
}

.eiq-run-report article {
  padding: 16px;
  border: 1px solid rgba(90,255,220,.08);
  background: rgba(255,255,255,.018);
}

.eiq-run-report article > strong {
  display: block;
  margin-top: 9px;
  font-size: 14px;
  line-height: 1.4;
}

.eiq-run-report dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0,1fr));
  gap: 8px 14px;
  margin: 14px 0 0;
}

.eiq-run-report dt {
  color: rgba(244,248,248,.45);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.eiq-run-report dd {
  margin: 2px 0 0;
  color: rgba(244,248,248,.88);
  font-size: 12px;
  font-weight: 700;
}

.eiq-run-report__reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 14px;
}

.eiq-run-report__reasons em {
  padding: 5px 8px;
  border: 1px solid rgba(90,255,220,.12);
  border-radius: 999px;
  color: rgba(244,248,248,.74);
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
}

.eiq-run-report footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 14px;
}

.eiq-run-report footer button {
  height: 30px;
  border: 0;
  background: transparent;
  color: #43efc6;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.eiq-compare-workspace {
  margin-top: 0;
  padding: 18px;
  border: 1px solid rgba(90,255,220,.10);
  border-radius: 10px;
  background: rgba(3,8,10,.62);
}

@media (max-width: 1300px) {
  .eiq-form-workbench__header,
  .eiq-horse-workbench-header,
  .eiq-analyst-summary,
  .eiq-form-toolbar,
  .eiq-run-report__grid {
    grid-template-columns: 1fr;
  }

  .eiq-horse-workbench-metrics {
    grid-template-columns: repeat(2, minmax(0,1fr));
  }
}
'''

text = path.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — PROFESSIONAL WORKBENCH V1" not in text:
    text += css
path.write_text(text, encoding="utf-8")

print("[EDGEIQ] Professional Form Workbench CSS applied")
print(f"[EDGEIQ] checkpoint: {backup}")
