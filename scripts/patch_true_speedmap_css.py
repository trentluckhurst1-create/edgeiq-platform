from pathlib import Path

css = Path(r".\src\edgeiq-speedmap-clean.css")

if css.exists():
    text = css.read_text(encoding="utf-8")
else:
    text = ""

text += r'''

/* TRUE SETTLING MAP V3 - FORCED */
.speed-runner-node.speed-row-banner {
  width: 122px !important;
  min-width: 122px !important;
  max-width: 122px !important;
  height: 26px !important;
  min-height: 26px !important;
  padding: 2px 5px !important;
}

.speed-runner-node.speed-row-banner img {
  width: 16px !important;
  height: 16px !important;
  flex: 0 0 16px !important;
}

.speed-runner-copy strong {
  font-size: 8px !important;
  letter-spacing: 0.01em !important;
  max-width: 78px !important;
}

.speed-runner-copy em {
  font-size: 6.5px !important;
}

.speed-track::before {
  content: "RAIL";
  position: absolute;
  left: 12px;
  bottom: 12px;
  color: rgba(110, 231, 183, 0.65);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.18em;
}

.speed-track::after {
  content: "WIDE";
  position: absolute;
  right: 12px;
  bottom: 12px;
  color: rgba(147, 197, 253, 0.55);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.18em;
}

.speed-grid-line {
  opacity: 0.14 !important;
}

.speed-tick {
  display: none !important;
}
'''

css.write_text(text, encoding="utf-8")
print("CREATED/PATCHED:", css)
