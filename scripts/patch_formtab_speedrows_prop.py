from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

# Pass current speed-map rows into the runner intelligence panel so it can show projected settling data
text = text.replace(
'''                    selectedCareerStats={selectedCareerStats}
                  />''',
'''                    selectedCareerStats={selectedCareerStats}
                    speedRows={currentSpeedRows}
                  />'''
)

path.write_text(text, encoding="utf-8")

print("APP PASSES SPEED ROWS TO RIGHT PANEL")
