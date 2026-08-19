from pathlib import Path

tsx = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = tsx.read_text(encoding="utf-8")

text = text.replace('                  <span className="col-truth">Truth</span>\n', '')
text = text.replace('                  <span className="col-suppression">Supp</span>', '                  <span className="col-suppression">Decision</span>')
text = text.replace('                  <span className="col-trust">Trust</span>\n', '')

text = text.replace('                      <span className="col-truth"><Chip value={discipline.truth?.truth_grade} tone={gradeTone(discipline.truth?.truth_grade)} /></span>\n', '')
text = text.replace('                      <span className="col-trust race-num">{firstText(discipline.execution?.execution_score, fmtScore(discipline.truth?.execution_trust_score))}</span>\n', '')

tsx.write_text(text, encoding="utf-8")
print("TSX BOARD COLUMNS CLEANED")

css = Path(r".\src\components\race-intelligence-screen.css")
css_text = css.read_text(encoding="utf-8")

old = 'grid-template-columns: 30px 34px minmax(318px, 1.65fr) 32px minmax(90px, 0.45fr) minmax(98px, 0.48fr) 48px 116px 48px 52px 66px 72px 44px;'
new = 'grid-template-columns: 30px 34px minmax(350px, 1.8fr) 32px minmax(92px, 0.45fr) minmax(104px, 0.5fr) 50px 116px 50px 54px 86px;'

if old not in css_text:
    raise SystemExit("Could not find board grid-template-columns. CSS not changed.")

css_text = css_text.replace(old, new)
css.write_text(css_text, encoding="utf-8")
print("CSS BOARD GRID CLEANED")
