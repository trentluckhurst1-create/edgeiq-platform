from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

text += r'''

/* STYLE 1 BENCHMARK BAR FINAL OVERRIDE */
.edgeiq-speed-row {
  grid-template-columns: 38px 220px 120px 70px 54px repeat(11, minmax(42px, 1fr)) !important;
  overflow: visible !important;
}

.edgeiq-speed-row .edgeiq-speed-bar-wrap {
  position: relative !important;
  grid-column: 6 / 17 !important;
  left: auto !important;
  right: auto !important;
  top: auto !important;
  bottom: auto !important;
  height: 22px !important;
  width: 100% !important;
  padding: 0 !important;
  display: block !important;
  background:
    repeating-linear-gradient(
      90deg,
      transparent 0,
      transparent calc(10% - 1px),
      rgba(148,163,184,.18) calc(10% - 1px),
      rgba(148,163,184,.18) 10%
    ) !important;
  border-left: 1px dashed rgba(148,163,184,.22) !important;
  z-index: 1 !important;
}

.edgeiq-speed-row .edgeiq-speed-bar {
  display: block !important;
  height: 100% !important;
  border-radius: 4px !important;
  min-width: 4px !important;
  background: linear-gradient(90deg, rgba(34,197,94,.72), rgba(74,222,128,.95)) !important;
}

.edgeiq-speed-row.edgeiq-speed-header {
  grid-template-columns: 38px 220px 120px 70px 54px repeat(11, minmax(42px, 1fr)) !important;
}

.edgeiq-speed-row.edgeiq-speed-header .scale {
  text-align: center !important;
}

.edgeiq-speed-row > span {
  position: relative !important;
  z-index: 2 !important;
}

@media (max-width: 1400px) {
  .edgeiq-speed-row,
  .edgeiq-speed-row.edgeiq-speed-header {
    grid-template-columns: 32px 170px 90px 56px 44px repeat(11, minmax(34px, 1fr)) !important;
  }
}
'''

path.write_text(text, encoding="utf-8")

print("APPLIED STYLE 1 BENCHMARK BAR FINAL CSS")
