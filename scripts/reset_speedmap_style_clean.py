from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-clean.css")

path.write_text(r'''
/* EDGEiQ SPEED MAP RESET — CLEAN PROFESSIONAL V1 */

.edgeiq-speed-shell {
  min-height: 560px !important;
  padding: 14px !important;
  background: #050b12 !important;
  border: 1px solid rgba(51, 65, 85, 0.9) !important;
  border-radius: 14px !important;
}

.speed-track {
  position: relative !important;
  min-height: 500px !important;
  overflow: hidden !important;
  border-radius: 12px !important;
  border: 1px solid rgba(71, 85, 105, 0.85) !important;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 12, 0.98)),
    repeating-linear-gradient(90deg, rgba(148, 163, 184, 0.07) 0px, rgba(148, 163, 184, 0.07) 1px, transparent 1px, transparent 120px),
    repeating-linear-gradient(180deg, rgba(148, 163, 184, 0.06) 0px, rgba(148, 163, 184, 0.06) 1px, transparent 1px, transparent 56px) !important;
}

.speed-label-grid {
  display: grid !important;
  grid-template-columns: repeat(4, 1fr) !important;
  gap: 6px !important;
  margin-bottom: 8px !important;
}

.speed-label {
  height: 28px !important;
  border-radius: 7px !important;
  background: #0f172a !important;
  color: #cbd5e1 !important;
  border: 1px solid rgba(71, 85, 105, 0.9) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
  letter-spacing: 0.16em !important;
}

.speed-label.leader,
.speed-label.onpace,
.speed-label.midfield,
.speed-label.backmarker {
  background: #0f172a !important;
  color: #cbd5e1 !important;
}

/* horse node = neutral, clear, not ugly colour blocks */
.speed-runner-node.speed-row-banner {
  width: 138px !important;
  min-width: 138px !important;
  max-width: 138px !important;
  height: 30px !important;
  min-height: 30px !important;
  transform: translate(-50%, -50%) !important;
  padding: 4px 7px !important;
  border-radius: 8px !important;
  background: #111827 !important;
  border: 1px solid rgba(100, 116, 139, 0.85) !important;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.24) !important;
  opacity: 0.96 !important;
}

.speed-runner-node.speed-row-banner.leader {
  border-left: 4px solid #f8fafc !important;
}

.speed-runner-node.speed-row-banner.onpace {
  border-left: 4px solid #94a3b8 !important;
}

.speed-runner-node.speed-row-banner.midfield {
  border-left: 4px solid #64748b !important;
}

.speed-runner-node.speed-row-banner.backmarker {
  border-left: 4px solid #334155 !important;
}

.speed-runner-node.speed-row-banner.selected {
  background: #172554 !important;
  border-color: #60a5fa !important;
  box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.9), 0 10px 26px rgba(37, 99, 235, 0.28) !important;
}

.speed-runner-node.speed-row-banner img {
  width: 17px !important;
  height: 17px !important;
  flex: 0 0 17px !important;
  border-radius: 3px !important;
}

.speed-runner-line,
.speed-grid-line,
.speed-tick {
  display: none !important;
}

.speed-runner-copy {
  min-width: 0 !important;
}

.speed-runner-copy strong {
  display: block !important;
  color: #f8fafc !important;
  max-width: 88px !important;
  font-size: 8px !important;
  line-height: 1.05 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.speed-runner-copy em {
  display: block !important;
  color: #94a3b8 !important;
  font-size: 6.5px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.speed-arrow {
  top: 12px !important;
  right: 14px !important;
  color: #94a3b8 !important;
  opacity: 0.75 !important;
  font-size: 9px !important;
}

.speed-track::before {
  content: "RAIL";
  position: absolute;
  left: 12px;
  bottom: 12px;
  color: #64748b;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.18em;
}

.speed-track::after {
  content: "WIDE";
  position: absolute;
  right: 12px;
  bottom: 12px;
  color: #64748b;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.18em;
}

.speed-rail {
  background: #475569 !important;
  opacity: 0.9 !important;
  width: 3px !important;
}
''', encoding="utf-8")

print("RESET SPEED MAP STYLE TO CLEAN PROFESSIONAL")
