from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

# Fix the benchmark scale/header so 100 stays in the header row.
text = re.sub(
r'''<div className="edgeiq-speed-row edgeiq-speed-header">[\s\S]*?</div>\s*\n\s*\{runners\.map''',
'''<div className="edgeiq-speed-row edgeiq-speed-header">
            <span>#</span>
            <span>Horse</span>
            <span>Jockey</span>
            <span>Barrier</span>
            <span>SPD</span>
            <span className="scale">0</span>
            <span className="scale">10</span>
            <span className="scale">20</span>
            <span className="scale">30</span>
            <span className="scale">40</span>
            <span className="scale">50</span>
            <span className="scale">60</span>
            <span className="scale">70</span>
            <span className="scale">80</span>
            <span className="scale">90</span>
            <span className="scale">100</span>
          </div>

          {runners.map''',
text,
count=1
)

# Ensure bar cell is rendered as normal grid content, not a broken absolute overlay.
text = text.replace(
'''                <div
                  className="edgeiq-speed-bar-wrap"
                  style={{ gridColumn: "6 / 17" }}
                >
                  <div
                    className={`edgeiq-speed-bar ${runner.mapPosition.replace(/\\s+/g, "-").toLowerCase()}`}
                    style={{ width: `${runner.spd}%` }}
                  />
                </div>''',
'''                <span className="edgeiq-speed-bar-wrap">
                  <i
                    className={`edgeiq-speed-bar ${runner.mapPosition.replace(/\\s+/g, "-").toLowerCase()}`}
                    style={{ width: `${runner.spd}%` }}
                  />
                </span>'''
)

path.write_text(text, encoding="utf-8")

print("FIXED SPEEDMAP HEADER AND BAR MARKUP")
