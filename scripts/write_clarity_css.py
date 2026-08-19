from pathlib import Path

css = Path(r".\src\edgeiq-clarity-pass.css")

css.write_text(r'''
/* ==========================================================
   EDGEiQ RACING — CLARITY PASS V1
   Goal: fewer boxes, clearer hierarchy, speed map dominance
   ========================================================== */

.edgeiq-race-workspace {
  display: grid !important;
  grid-template-columns: 300px minmax(620px, 1.35fr) 360px !important;
  grid-template-areas:
    "left centre right"
    "bottom bottom bottom" !important;
  gap: 12px !important;
  align-items: start !important;
}

.edgeiq-race-left {
  grid-area: left !important;
  max-height: calc(100vh - 285px) !important;
  overflow: hidden !important;
}

.edgeiq-race-centre {
  grid-area: centre !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 10px !important;
}

.edgeiq-race-right {
  grid-area: right !important;
  max-height: calc(100vh - 285px) !important;
  overflow: hidden !important;
}

.edgeiq-race-bottom {
  grid-area: bottom !important;
}

/* Runner list: make it clean and scan-first */
.edgeiq-runner-decision-table {
  display: flex !important;
  flex-direction: column !important;
  gap: 5px !important;
  max-height: calc(100vh - 340px) !important;
  overflow: auto !important;
  padding-right: 3px !important;
}

.edgeiq-runner-decision-row {
  min-height: 30px !important;
  grid-template-columns: 28px minmax(0, 1fr) 46px 46px 56px 48px !important;
  border-radius: 8px !important;
  background: rgba(7, 18, 25, 0.78) !important;
  border: 1px solid rgba(96, 165, 250, 0.13) !important;
}

.edgeiq-runner-decision-row.active {
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.22), rgba(15, 23, 42, 0.92)) !important;
  border-color: rgba(52, 211, 153, 0.7) !important;
  box-shadow: inset 3px 0 0 rgba(52, 211, 153, 0.95) !important;
}

.edgeiq-runner-decision-row .runner {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

/* Speed map: make it the hero */
.edgeiq-speed {
  gap: 9px !important;
}

.edgeiq-speed-head {
  padding: 10px 12px !important;
  border-color: rgba(52, 211, 153, 0.28) !important;
  background: linear-gradient(90deg, rgba(6, 24, 31, 0.96), rgba(8, 13, 23, 0.96)) !important;
}

.edgeiq-speed-head .edgeiq-ws-kicker {
  color: #5eead4 !important;
  letter-spacing: 0.18em !important;
}

.speed-sub {
  color: #9fb3c8 !important;
  font-size: 11px !important;
}

.speed-pills span,
.edgeiq-scr-toggle {
  border-radius: 8px !important;
  padding: 6px 9px !important;
  background: rgba(15, 23, 42, 0.95) !important;
}

/* Reduce small-card chaos */
.speed-bias-card {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 8px !important;
  padding: 9px !important;
}

.speed-bias-card > div {
  min-height: 54px !important;
  padding: 8px 9px !important;
  border-radius: 9px !important;
  background: rgba(6, 14, 22, 0.78) !important;
  border: 1px solid rgba(148, 163, 184, 0.12) !important;
}

.speed-bias-card span {
  font-size: 9px !important;
  letter-spacing: 0.12em !important;
  color: #8ea4ba !important;
}

.speed-bias-card strong {
  font-size: 15px !important;
  line-height: 1.05 !important;
}

.speed-intel-card {
  border-color: rgba(52, 211, 153, 0.28) !important;
}

/* Main map canvas */
.edgeiq-speed-shell {
  padding: 10px !important;
  min-height: 520px !important;
  background:
    radial-gradient(circle at 50% 0%, rgba(20, 184, 166, 0.10), transparent 34%),
    linear-gradient(180deg, rgba(8, 15, 25, 0.98), rgba(3, 7, 12, 0.98)) !important;
}

.speed-track {
  min-height: 470px !important;
  border-radius: 16px !important;
  background:
    linear-gradient(90deg, rgba(34, 197, 94, 0.08), transparent 18%, transparent 82%, rgba(59, 130, 246, 0.07)),
    repeating-linear-gradient(180deg, rgba(148, 163, 184, 0.08) 0, rgba(148, 163, 184, 0.08) 1px, transparent 1px, transparent 34px),
    rgba(2, 6, 12, 0.96) !important;
}

.speed-label-grid {
  gap: 6px !important;
  margin-bottom: 7px !important;
}

.speed-label {
  border-radius: 8px !important;
  padding: 7px 8px !important;
  font-size: 10px !important;
  letter-spacing: 0.13em !important;
}

/* Runner banners: slimmer, readable */
.speed-runner-node.speed-row-banner {
  min-height: 24px !important;
  max-width: 275px !important;
  border-radius: 7px !important;
  padding: 3px 8px !important;
  opacity: 0.92 !important;
}

.speed-runner-node.speed-row-banner.selected {
  opacity: 1 !important;
  border-color: rgba(52, 211, 153, 0.95) !important;
  box-shadow: 0 0 0 1px rgba(52, 211, 153, 0.55), 0 0 18px rgba(52, 211, 153, 0.22) !important;
}

.speed-runner-copy strong {
  font-size: 10px !important;
  max-width: 190px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.speed-runner-copy em {
  font-size: 8px !important;
  opacity: 0.82 !important;
}

/* Right panel: selected runner only, less tile noise */
.edgeiq-form-tab {
  gap: 9px !important;
}

.edgeiq-form-rail.runner-tile-grid {
  max-height: 190px !important;
  overflow: auto !important;
  display: grid !important;
  grid-template-columns: 1fr !important;
  gap: 5px !important;
  padding: 8px !important;
}

.form-runner-tile {
  min-height: 30px !important;
  grid-template-columns: 28px 28px minmax(0, 1fr) 44px !important;
  border-radius: 8px !important;
}

.form-runner-tile .name {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.edgeiq-form-layout {
  display: block !important;
}

.edgeiq-form-summary {
  padding: 12px !important;
}

.summary-runner h2 {
  font-size: 18px !important;
  line-height: 1.1 !important;
}

.summary-grid {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 7px !important;
}

.summary-grid > div,
.summary-records > div {
  min-height: 54px !important;
  border-radius: 10px !important;
}

.summary-records {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 7px !important;
}

.edgeiq-form-main {
  margin-top: 9px !important;
  max-height: 260px !important;
  overflow: auto !important;
}

/* Market movers should not compete with speed map */
.edgeiq-market-drawer {
  border: 1px solid rgba(56, 189, 248, 0.18) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  background: rgba(3, 10, 16, 0.88) !important;
}

.edgeiq-market-drawer > summary {
  cursor: pointer !important;
  list-style: none !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  padding: 10px 12px !important;
  color: #67e8f9 !important;
  font-weight: 900 !important;
  font-size: 11px !important;
  letter-spacing: 0.18em !important;
}

.edgeiq-market-drawer > summary::-webkit-details-marker {
  display: none !important;
}

.edgeiq-market-drawer > summary span {
  color: #94a3b8 !important;
  font-size: 10px !important;
  letter-spacing: 0.08em !important;
}

/* Execution drawer: collapsed by default, command-bar style */
.edgeiq-execution-drawer {
  margin-top: 2px !important;
  border: 1px solid rgba(16, 185, 129, 0.32) !important;
  border-radius: 16px !important;
  overflow: hidden !important;
  background:
    linear-gradient(90deg, rgba(5, 31, 26, 0.96), rgba(5, 11, 18, 0.96)) !important;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.28) !important;
}

.edgeiq-execution-drawer > summary {
  cursor: pointer !important;
  list-style: none !important;
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto auto !important;
  align-items: center !important;
  gap: 14px !important;
  min-height: 48px !important;
  padding: 0 14px !important;
}

.edgeiq-execution-drawer > summary::-webkit-details-marker {
  display: none !important;
}

.edgeiq-execution-drawer > summary span {
  color: #5eead4 !important;
  font-size: 12px !important;
  font-weight: 1000 !important;
  letter-spacing: 0.18em !important;
}

.edgeiq-execution-drawer > summary strong {
  color: #fff !important;
  font-size: 12px !important;
  font-weight: 900 !important;
}

.edgeiq-execution-drawer > summary em {
  color: #94a3b8 !important;
  font-size: 11px !important;
  font-style: normal !important;
}

.edgeiq-execution-drawer:not([open]) {
  max-height: 52px !important;
}

.edgeiq-execution-drawer[open] {
  max-height: 760px !important;
  overflow: auto !important;
}

/* Kill excess vertical bloat in execution when opened */
.edgeiq-execution-drawer .grid {
  gap: 6px !important;
}

.edgeiq-execution-drawer section,
.edgeiq-execution-drawer > div {
  max-width: 100% !important;
}

/* General terminal clarity */
.terminal-card {
  border-color: rgba(71, 85, 105, 0.38) !important;
  box-shadow: none !important;
}

.edgeiq-panel-title {
  color: #e2e8f0 !important;
  letter-spacing: 0.18em !important;
}

@media (max-width: 1300px) {
  .edgeiq-race-workspace {
    grid-template-columns: 280px minmax(540px, 1fr) 320px !important;
  }

  .edgeiq-speed-shell {
    min-height: 470px !important;
  }

  .speed-track {
    min-height: 420px !important;
  }
}
''', encoding="utf-8")

print("WROTE edgeiq-clarity-pass.css")
