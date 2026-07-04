from pathlib import Path

path = Path(r".\src\edgeiq-vic-stability-pass.css")
text = path.read_text(encoding="utf-8")

text += r'''

/* LEFT RUNNER DECISION LADDER */
.edgeiq-runner-ladder-head {
  display: grid;
  grid-template-columns: 26px minmax(110px, 1fr) 44px 44px 50px 58px 54px;
  gap: 6px;
  padding: 8px 8px 6px;
  color: #64748b;
  font-size: 8px;
  font-weight: 900;
  letter-spacing: 0.12em;
  border-bottom: 1px solid rgba(51,65,85,.75);
}

.edgeiq-runner-decision-table {
  max-height: 620px !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}

.edgeiq-runner-decision-row {
  display: grid !important;
  grid-template-columns: 26px minmax(110px, 1fr) 44px 44px 50px 58px 54px !important;
  gap: 6px !important;
  align-items: center !important;
  min-height: 34px !important;
  padding: 0 8px !important;
  border-radius: 0 !important;
  border-left: 0 !important;
  border-right: 0 !important;
  border-top: 0 !important;
  border-bottom: 1px solid rgba(51,65,85,.55) !important;
  background: rgba(3, 10, 16, 0.78) !important;
}

.edgeiq-runner-decision-row:hover {
  background: rgba(15, 23, 42, 0.95) !important;
}

.edgeiq-runner-decision-row.active {
  background: linear-gradient(90deg, rgba(16,185,129,.22), rgba(15,23,42,.92)) !important;
  box-shadow: inset 3px 0 0 rgba(52,211,153,.95) !important;
}

.edgeiq-runner-decision-row .num {
  color: #bfdbfe !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  text-align: center !important;
}

.edgeiq-runner-decision-row .runner {
  color: #f8fafc !important;
  font-size: 9px !important;
  font-weight: 900 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.edgeiq-runner-decision-row .price {
  color: #dbeafe !important;
  font-size: 9px !important;
  font-weight: 800 !important;
  text-align: right !important;
}

.edgeiq-runner-decision-row .edge-pos {
  color: #34d399 !important;
  font-size: 9px !important;
  font-weight: 950 !important;
  text-align: right !important;
}

.edgeiq-runner-decision-row .edge-muted {
  color: #64748b !important;
  font-size: 9px !important;
  font-weight: 800 !important;
  text-align: right !important;
}

.edgeiq-runner-decision-row .map {
  color: #93c5fd !important;
  font-size: 7px !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.edgeiq-runner-decision-row .action {
  border-radius: 999px !important;
  padding: 4px 6px !important;
  font-size: 8px !important;
  font-weight: 950 !important;
  text-align: center !important;
  background: rgba(15,23,42,.95) !important;
  border: 1px solid rgba(71,85,105,.75) !important;
  color: #cbd5e1 !important;
}

.edgeiq-runner-decision-row .action-bet,
.edgeiq-runner-decision-row .action-play {
  color: #34d399 !important;
  border-color: rgba(52,211,153,.5) !important;
}

.edgeiq-runner-decision-row .action-wait {
  color: #fbbf24 !important;
  border-color: rgba(251,191,36,.45) !important;
}

.edgeiq-runner-decision-row .action-suppressed,
.edgeiq-runner-decision-row .action-supp {
  color: #fb7185 !important;
  border-color: rgba(251,113,133,.45) !important;
}
'''

path.write_text(text, encoding="utf-8")

print("PATCHED LEFT LADDER CSS")
