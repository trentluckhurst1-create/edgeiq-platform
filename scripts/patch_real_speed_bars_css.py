from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

text += r'''

/* REAL BENCHMARK SPEED BARS */
.edgeiq-speed-bar-wrap {
  position: absolute;
  left: calc(38px + 220px + 120px + 70px + 54px);
  right: 14px;
  top: 8px;
  bottom: 8px;
  display: flex;
  align-items: center;
  pointer-events: none;
  z-index: 0;
}

.edgeiq-speed-bar {
  height: 20px;
  border-radius: 4px;
  opacity: 0.95;
  transition: width 0.2s ease;
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,0.06),
    0 0 12px rgba(0,0,0,0.22);
}

.edgeiq-speed-bar.leader {
  background: linear-gradient(90deg, rgba(34,197,94,0.95), rgba(134,239,172,0.92));
}

.edgeiq-speed-bar.on-pace {
  background: linear-gradient(90deg, rgba(59,130,246,0.95), rgba(147,197,253,0.92));
}

.edgeiq-speed-bar.midfield {
  background: linear-gradient(90deg, rgba(34,197,94,0.78), rgba(74,222,128,0.92));
}

.edgeiq-speed-bar.backmarker {
  background: linear-gradient(90deg, rgba(168,85,247,0.95), rgba(196,181,253,0.92));
}

.edgeiq-speed-row {
  overflow: hidden;
}

.edgeiq-speed-row > span {
  position: relative;
  z-index: 2;
}

.edgeiq-speed-row .horse strong {
  position: relative;
  z-index: 3;
}

@media (max-width: 1400px) {
  .edgeiq-speed-bar-wrap {
    left: calc(32px + 170px + 90px + 56px + 44px);
  }
}
'''

path.write_text(text, encoding="utf-8")

print("PATCHED REAL SPEED BARS CSS")
