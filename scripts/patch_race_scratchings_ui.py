from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "components" / "race-intelligence-screen.css"

content = TSX.read_text(encoding="utf-8")

helper = r'''
function isScratchedRunner(row: any): boolean {
  const values = [
    row?.is_scratched,
    row?.scratched,
    row?.scratch_status,
    row?.runner_status,
    row?.status,
    row?.ui_action,
    row?.execution_action,
  ].map((value) => String(value ?? "").trim().toUpperCase());

  return values.some((value) =>
    value === "1" ||
    value === "Y" ||
    value === "YES" ||
    value === "TRUE" ||
    value === "SCR" ||
    value.includes("SCRATCH") ||
    value.includes("WITHDRAWN")
  );
}
'''

if "function isScratchedRunner" not in content:
    content = content.replace("export default function RaceIntelligenceScreen", helper + "\nexport default function RaceIntelligenceScreen")

content = re.sub(
    r'className=\{`race-field-runner([^`]*)`\}',
    r'className={`race-field-runner\1${isScratchedRunner(row) ? " is-scratched" : ""}`}',
    content,
)

content = re.sub(
    r'className=\{`race-board-runner([^`]*)`\}',
    r'className={`race-board-runner\1${isScratchedRunner(row) ? " is-scratched" : ""}`}',
    content,
)

content = content.replace(
    'className="race-field-runner"',
    'className={`race-field-runner${isScratchedRunner(row) ? " is-scratched" : ""}`}'
)

content = content.replace(
    'className="race-board-runner"',
    'className={`race-board-runner${isScratchedRunner(row) ? " is-scratched" : ""}`}'
)

TSX.write_text(content, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")

scratch_css = r'''

/* EDGEIQ SCRATCHINGS */
.race-field-runner.is-scratched,
.race-board-runner.is-scratched {
  opacity: 0.46;
  background: rgba(15, 23, 42, 0.34) !important;
  box-shadow: inset 3px 0 0 rgba(148, 163, 184, 0.28) !important;
}

.race-field-runner.is-scratched .race-field-horse strong,
.race-board-runner.is-scratched .runner-name-copy strong,
.race-field-runner.is-scratched .runner-name-copy strong {
  color: #94a3b8 !important;
  text-decoration: line-through;
  text-decoration-thickness: 2px;
  text-decoration-color: rgba(248, 113, 113, 0.9);
}

.race-field-runner.is-scratched .col-live,
.race-field-runner.is-scratched .col-fluc,
.race-field-runner.is-scratched .col-fair,
.race-field-runner.is-scratched .col-edge,
.race-board-runner.is-scratched .col-live,
.race-board-runner.is-scratched .col-fluc,
.race-board-runner.is-scratched .col-fair,
.race-board-runner.is-scratched .col-edge {
  color: transparent !important;
  text-shadow: none !important;
}

.race-field-runner.is-scratched .col-live::after,
.race-board-runner.is-scratched .col-live::after {
  content: "SCR";
  color: #f87171;
  font-size: 9px;
  font-weight: 950;
  letter-spacing: 0.12em;
}

.race-field-runner.is-scratched .race-action,
.race-board-runner.is-scratched .race-decision,
.race-board-runner.is-scratched .race-action {
  border-color: rgba(248, 113, 113, 0.36) !important;
  background: rgba(248, 113, 113, 0.10) !important;
  color: #fca5a5 !important;
}

.race-field-runner.is-scratched .race-action::before,
.race-board-runner.is-scratched .race-decision::before,
.race-board-runner.is-scratched .race-action::before {
  content: "SCRATCHED";
}

.race-field-runner.is-scratched .race-action,
.race-board-runner.is-scratched .race-decision,
.race-board-runner.is-scratched .race-action {
  font-size: 0 !important;
}

.race-field-runner.is-scratched .race-action::before,
.race-board-runner.is-scratched .race-decision::before,
.race-board-runner.is-scratched .race-action::before {
  font-size: 8px !important;
}
'''

if "EDGEIQ SCRATCHINGS" not in css:
    css += scratch_css

CSS.write_text(css, encoding="utf-8")

print("SCRATCHINGS UI PATCH APPLIED")
