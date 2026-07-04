from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

anchor = """        <div>
          <span>PACE COLLAPSE RISK</span>
          <strong>
            {realCollapseRisk}
          </strong>
        </div>
"""

insert = """        <div>
          <span>PACE COLLAPSE RISK</span>
          <strong>
            {realCollapseRisk}
          </strong>
        </div>

        <div>
          <span>PRESSURE INDEX</span>
          <strong>
            {pressureIndex || "-"}
          </strong>
        </div>

        <div>
          <span>SHAPE CONFIDENCE</span>
          <strong>
            {shapeConfidence}
          </strong>
        </div>

        <div>
          <span>TOP SECTIONAL</span>
          <strong>
            {topSectionalHorse || "-"}
          </strong>
          <small>
            {topSectionalScore > 0 ? topSectionalScore.toFixed(1) : "-"}
          </small>
        </div>
"""

if anchor not in text:
    raise SystemExit("TACTICAL UI ANCHOR NOT FOUND")

text = text.replace(anchor, insert, 1)

path.write_text(text, encoding="utf-8")

print("INSERTED TACTICAL RACE SHAPE PANELS")
