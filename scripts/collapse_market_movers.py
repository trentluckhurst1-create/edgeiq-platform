from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''                <SpeedMapTab data={currentSpeedRows} paceRows={currentPacePressureRows} raceShape={currentRaceShapeRow} selectedMeeting={currentMeeting?.track} selectedHorse={selectedRunner?.horse ?? ""} biasProfile={trackBiasRows} raceDistance={currentRace?.distance ?? null} trackCondition={currentRace?.todayTrackCondition ?? ""} onSelectHorse={(horse) => { const found = currentRace?.rows.find((row) => compactKey(row.horse) === compactKey(horse)); if (found) setSelectedHorseKey(found.horseKey); }} />
                <LiveMarketMovers />'''

new = '''                <SpeedMapTab data={currentSpeedRows} paceRows={currentPacePressureRows} raceShape={currentRaceShapeRow} selectedMeeting={currentMeeting?.track} selectedHorse={selectedRunner?.horse ?? ""} biasProfile={trackBiasRows} raceDistance={currentRace?.distance ?? null} trackCondition={currentRace?.todayTrackCondition ?? ""} onSelectHorse={(horse) => { const found = currentRace?.rows.find((row) => compactKey(row.horse) === compactKey(horse)); if (found) setSelectedHorseKey(found.horseKey); }} />
                <details className="edgeiq-market-drawer">
                  <summary>LIVE MARKET MOVERS <span>Steam + Drift Monitor</span></summary>
                  <LiveMarketMovers />
                </details>'''

if old not in text:
    raise SystemExit("Market movers block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

print("COLLAPSED Market Movers INTO COMPACT DRAWER")
