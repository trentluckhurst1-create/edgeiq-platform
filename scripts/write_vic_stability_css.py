from pathlib import Path

path = Path(r".\src\edgeiq-vic-stability-pass.css")

path.write_text(r'''
/* EDGEiQ VIC STABILITY PASS */

.edgeiq-race-workspace {
  display: grid !important;
  grid-template-columns: 280px minmax(520px, 1fr) 360px !important;
  grid-template-areas:
    "left centre right"
    "bottom bottom bottom" !important;
  gap: 12px !important;
  align-items: start !important;
  overflow: hidden !important;
}

.edgeiq-race-left { grid-area: left !important; min-width: 0 !important; }
.edgeiq-race-centre { grid-area: centre !important; min-width: 0 !important; overflow: hidden !important; }
.edgeiq-race-right { grid-area: right !important; min-width: 0 !important; overflow: hidden !important; position: relative !important; z-index: 1 !important; }
.edgeiq-race-bottom { grid-area: bottom !important; min-width: 0 !important; }

.speedmap-pro {
  width: 100% !important;
  max-width: 100% !important;
  overflow: hidden !important;
}

.speedmap-pro-head {
  grid-template-columns: 190px minmax(0, 1fr) !important;
  gap: 10px !important;
}

.speedmap-pro-metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

.speedmap-pro-track {
  min-height: 430px !important;
  max-height: 430px !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 8px !important;
  overflow: hidden !important;
}

.speedmap-lane-column {
  min-width: 0 !important;
  overflow: hidden !important;
}

.speedmap-lane-runners {
  gap: 5px !important;
  padding: 7px !important;
}

.speedmap-pro-runner {
  grid-template-columns: 20px 20px minmax(0, 1fr) 26px !important;
  min-height: 30px !important;
  padding: 4px 6px !important;
}

.speedmap-name {
  font-size: 8px !important;
}

.speedmap-meta {
  font-size: 7px !important;
}

.edgeiq-form-rail {
  max-height: 330px !important;
  overflow: auto !important;
}

.edgeiq-form-summary {
  max-height: 360px !important;
  overflow: auto !important;
}

.edgeiq-form-main {
  max-height: 260px !important;
  overflow: auto !important;
}

.edgeiq-market-drawer,
.edgeiq-execution-drawer {
  max-width: 100% !important;
  overflow: hidden !important;
}

@media (max-width: 1400px) {
  .edgeiq-race-workspace {
    grid-template-columns: 260px minmax(480px, 1fr) 330px !important;
  }
}
''', encoding="utf-8")

print("WROTE VIC STABILITY CSS")
