from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''            {currentRace ? (
              <div className="edgeiq-current-race-detail">
                <span>{currentRace.raceDate}</span>
                <span>{displayUserLocalRaceTime(currentRace.rows[0], currentRace)}</span>
                <span>{currentRace.track}</span>
                <span>R{currentRace.raceNo}</span>
                <span>{currentRace.rows[0]?.distance ? `${currentRace.rows[0].distance}m` : "-"}</span>
                <span>{currentRace.rows[0]?.raceClass || "-"}</span>
                <span className={`condition-pill ${conditionClassName(currentRace.rows[0]?.todayTrackCondition)}`}>
                  {(currentRace.rows[0]?.todayTrackCondition || "-").toUpperCase()}
                </span>'''

new = '''            {currentRace ? (
              <div className="edgeiq-current-race-detail">
                <span>DATE {currentRace.raceDate}</span>
                <span>TIME {displayUserLocalRaceTime(currentRace.rows[0], currentRace)}</span>
                <span className={`condition-pill ${conditionClassName(currentRace.rows[0]?.todayTrackCondition)}`}>
                  TRACK {(currentRace.rows[0]?.todayTrackCondition || currentRace.todayTrackCondition || "-").toUpperCase()}
                </span>
                <span>RACE R{currentRace.raceNo}</span>
                <span>DIST {currentRace.rows[0]?.distance || currentRace.distance ? `${currentRace.rows[0]?.distance ?? currentRace.distance}m` : "-"}</span>
                <span>CLASS {currentRace.rows[0]?.raceClass || currentRace.raceClass || "-"}</span>'''

if old not in text:
    raise SystemExit("CURRENT_RACE_DETAIL_BLOCK_NOT_FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("APP_CURRENT_RACE_HEADER_REWIRED")
