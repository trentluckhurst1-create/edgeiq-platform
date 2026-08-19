from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

# REMOVE OLD TRACK RENDER BLOCK
pattern = r'return \(\s*<section className="edgeiq-speed terminal-panel-stack">[\s\S]*?</section>\s*\);'

replacement = r'''
return (
<section className="edgeiq-speed terminal-panel-stack">

  <div className="edgeiq-speed-head terminal-card">
    <div className="speed-head-title">
      <span>EDGEIQ TRUE SPEED MAP</span>
      <small>200M SETTLING POSITIONS</small>
    </div>

    <div className="speed-head-metrics">
      <div className="speed-chip">
        <label>RUNNERS</label>
        <strong>{runners.length}</strong>
      </div>

      <div className="speed-chip">
        <label>TEMPO</label>
        <strong>{realTempoShape}</strong>
      </div>

      <div className="speed-chip">
        <label>PRESSURE</label>
        <strong>{pressureLabel}</strong>
      </div>

      <div className="speed-chip">
        <label>TRACK</label>
        <strong>{rightHanded ? "RIGHT" : "LEFT"} HANDED</strong>
      </div>
    </div>
  </div>

  <div className="speedmap-v2-shell">

    <div className="speedmap-lane-header">
      <div>LEADERS</div>
      <div>ON PACE</div>
      <div>MIDFIELD</div>
      <div>BACKMARKERS</div>
    </div>

    <div className="speedmap-track">

      <div className="speedmap-rail" />

      {plotted.map((runner: any) => (
        <button
          key={runner.horse}
          className={`speedmap-runner ${styleClass(runner.mapPosition)} ${selectedHorse === runner.horse ? "selected" : ""}`}
          style={{
            left: `${runner.x}%`,
            top: `${runner.y}%`
          }}
          onClick={() => onSelectHorse?.(runner.horse)}
        >
          <img src={runner.silkUrl} alt="" />

          <div className="speedmap-copy">
            <strong>
              {runner.saddlecloth}. {runner.horse}
            </strong>

            <span>
              BAR {runner.barrier} | {runner.mapPosition}
            </span>
          </div>
        </button>
      ))}

      <div className="speedmap-direction">
        ← RACE DIRECTION
      </div>

      <div className="speedmap-rail-label">
        RAIL
      </div>

      <div className="speedmap-wide-label">
        WIDE
      </div>

    </div>

  </div>

</section>
);
'''

text = re.sub(pattern, replacement, text)

path.write_text(text, encoding="utf-8")

print("REBUILT SPEED MAP LAYOUT")
