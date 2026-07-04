from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''                <span className={`condition-pill ${conditionClassName(currentRace.rows[0]?.todayTrackCondition || currentRace.todayTrackCondition)}`}>
                  {(currentRace.rows[0]?.todayTrackCondition || currentRace.todayTrackCondition || "-").toUpperCase()}
                </span>'''

new = '''                <span>
                  <em className={`edgeiq-condition-text ${conditionClassName(currentRace.rows[0]?.todayTrackCondition || currentRace.todayTrackCondition)}`}>
                    {(currentRace.rows[0]?.todayTrackCondition || currentRace.todayTrackCondition || "-").toUpperCase()}
                  </em>
                </span>'''

if old not in text:
    raise SystemExit("CONDITION_PILL_BLOCK_NOT_FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("APP_CONDITION_TEXT_ONLY_COMPLETE")
