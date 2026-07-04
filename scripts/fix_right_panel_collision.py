from pathlib import Path

path = Path(r".\src\edgeiq-vic-stability-pass.css")
text = path.read_text(encoding="utf-8")

text += r'''

/* FIX RIGHT PANEL COLLISION */
.edgeiq-race-workspace {
  grid-template-columns: 260px minmax(560px, 1fr) 330px !important;
  overflow: visible !important;
}

.edgeiq-race-centre {
  overflow: visible !important;
  z-index: 1 !important;
}

.edgeiq-race-right {
  position: relative !important;
  z-index: 3 !important;
  background: #020617 !important;
  border-left: 1px solid rgba(51,65,85,.8) !important;
  padding-left: 8px !important;
}

.edgeiq-race-right .edgeiq-form-tab {
  position: relative !important;
  z-index: 4 !important;
  background: #020617 !important;
}

/* STOP runner grid from floating over profile */
.edgeiq-form-rail.runner-tile-grid {
  max-height: 520px !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  background: #050b12 !important;
  border: 1px solid rgba(51,65,85,.75) !important;
  border-radius: 12px !important;
}

/* Hide duplicated right profile until right rail is rebuilt */
.edgeiq-form-layout {
  display: none !important;
}

/* make centre breathe */
.speedmap-pro-track {
  max-height: 470px !important;
  min-height: 470px !important;
}

.speedmap-lane-runners {
  max-height: 405px !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}

.speedmap-pro-metrics div {
  min-width: 0 !important;
}

.speedmap-pro-metrics strong {
  max-width: 100% !important;
}
'''

path.write_text(text, encoding="utf-8")
print("PATCHED RIGHT PANEL COLLISION")
