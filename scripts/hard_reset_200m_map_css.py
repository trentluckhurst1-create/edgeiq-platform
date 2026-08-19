from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-clean.css")
text = path.read_text(encoding="utf-8") if path.exists() else ""

text += r'''

/* HARD RESET — 200M SETTLING MAP */
.speed-track {
  min-height: 520px !important;
  background:
    linear-gradient(180deg, rgba(16,185,129,0.10), rgba(2,6,12,0.98)),
    repeating-linear-gradient(90deg, rgba(148,163,184,0.10) 0px, rgba(148,163,184,0.10) 1px, transparent 1px, transparent 130px),
    repeating-linear-gradient(180deg, rgba(148,163,184,0.08) 0px, rgba(148,163,184,0.08) 1px, transparent 1px, transparent 52px) !important;
}

.speed-runner-node.speed-row-banner {
  width: 132px !important;
  min-width: 132px !important;
  max-width: 132px !important;
  height: 30px !important;
  min-height: 30px !important;
  transform: translate(-50%, -50%) !important;
  padding: 4px 6px !important;
  border-radius: 9px !important;
  border: 1px solid rgba(255,255,255,0.22) !important;
}

.speed-runner-node.speed-row-banner img {
  width: 17px !important;
  height: 17px !important;
}

.speed-runner-copy strong {
  max-width: 86px !important;
  font-size: 8px !important;
}

.speed-runner-copy em {
  font-size: 6.5px !important;
}

.speed-runner-line,
.speed-grid-line,
.speed-tick {
  display: none !important;
}

.speed-arrow {
  top: 10px !important;
  right: 12px !important;
}
'''

path.write_text(text, encoding="utf-8")
print("APPLIED hard reset 200m map CSS")
