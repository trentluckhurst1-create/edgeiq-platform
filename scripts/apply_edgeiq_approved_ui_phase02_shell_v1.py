from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE02_SHELL_{STAMP}"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def checkpoint(paths: list[Path]) -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            target = CHECKPOINT / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def patch_main() -> None:
    path = ROOT / "src" / "main.tsx"
    text = read(path)
    import_line = 'import "./edgeiq-os/approved-ui/edgeiqApprovedUiRebuildV1.css";'
    if import_line not in text:
        marker = 'import "./edgeiq-os/design-system/edgeiqDesignSystem.css";'
        if marker not in text:
            raise SystemExit("main.tsx import marker missing")
        text = text.replace(marker, marker + "\n" + import_line)
    write(path, text)


def patch_app_navigation() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "AppNavigation.tsx"
    text = read(path)
    marker = 'const navItems: Array<{ key: GlobalSection; label: string }> = ['
    if marker not in text:
        raise SystemExit("AppNavigation nav marker missing")
    text = text.replace(
        'const navItems: Array<{ key: GlobalSection; label: string }> = [',
        'const navItems: Array<{ key: GlobalSection; label: string; icon: string }> = [',
    )
    replacements = {
        '{ key: "home", label: "HOME" }': '{ key: "home", label: "HOME", icon: "H" }',
        '{ key: "meetings", label: "MEETINGS" }': '{ key: "meetings", label: "MEETINGS", icon: "M" }',
        '{ key: "race", label: "RACE" }': '{ key: "race", label: "RACE", icon: "R" }',
        '{ key: "field", label: "FIELD" }': '{ key: "field", label: "FIELD", icon: "F" }',
        '{ key: "formGuide", label: "FORM GUIDE" }': '{ key: "formGuide", label: "FORM GUIDE", icon: "G" }',
        '{ key: "performance", label: "PERFORMANCE" }': '{ key: "performance", label: "PERFORMANCE", icon: "P" }',
        '{ key: "epi", label: "EPI" }': '{ key: "epi", label: "EPI", icon: "E" }',
        '{ key: "map", label: "MAP" }': '{ key: "map", label: "MAP", icon: "A" }',
        '{ key: "market", label: "MARKET" }': '{ key: "market", label: "MARKET", icon: "$" }',
        '{ key: "overview", label: "OVERVIEW" }': '{ key: "overview", label: "OVERVIEW", icon: "O" }',
        '{ key: "insights", label: "INSIGHTS" }': '{ key: "insights", label: "INSIGHTS", icon: "I" }',
        '{ key: "results", label: "RESULTS" }': '{ key: "results", label: "RESULTS", icon: "R" }',
        '{ key: "lab", label: "LAB" }': '{ key: "lab", label: "LAB", icon: "L" }',
        '{ key: "compare", label: "COMPARE" }': '{ key: "compare", label: "COMPARE", icon: "C" }',
        '{ key: "review", label: "REVIEW" }': '{ key: "review", label: "REVIEW", icon: "V" }',
        '{ key: "settings", label: "SETTINGS" }': '{ key: "settings", label: "SETTINGS", icon: "S" }',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    old_button = """          <button
            key={item.key}
            type="button"
            className={activeSection === item.key ? "is-active" : ""}
            onClick={() => onSectionChange(item.key)}
          >
            {item.label}
          </button>"""
    new_button = """          <button
            key={item.key}
            type="button"
            className={activeSection === item.key ? "is-active" : ""}
            onClick={() => onSectionChange(item.key)}
          >
            <span aria-hidden="true">{item.icon}</span>
            <strong>{item.label}</strong>
          </button>"""
    if old_button not in text and new_button not in text:
        raise SystemExit("AppNavigation button marker missing")
    text = text.replace(old_button, new_button)
    write(path, text)


def patch_workspace_shell() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "WorkspaceShell.tsx"
    text = """import type { ReactNode } from "react";
import { AppNavigation, type GlobalSection } from "./AppNavigation";

type WorkspaceShellProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
  eyebrow: string;
  title: string;
  meta?: string;
  children: ReactNode;
};

function formatHeaderDate() {
  return new Intl.DateTimeFormat("en-AU", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date()).toUpperCase();
}

function formatHeaderTime() {
  return new Intl.DateTimeFormat("en-AU", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(new Date());
}

export function WorkspaceShell({
  activeSection,
  onSectionChange,
  children,
}: WorkspaceShellProps) {
  return (
    <section className="eiq-approved-shell" data-edgeiq-approved-ui="v1">
      <AppNavigation activeSection={activeSection} onSectionChange={onSectionChange} />

      <div className="eiq-approved-shell__frame">
        <header className="eiq-approved-topbar">
          <div className="eiq-approved-topbar__identity">
            <strong>EDGEiQ PROFESSIONAL RACING INTELLIGENCE OPERATING SYSTEM</strong>
            <span>Information is not Intelligence. Evidence leads. Precision decides.</span>
          </div>
          <div className="eiq-approved-topbar__ops" aria-label="Operational context">
            <span>{formatHeaderDate()}</span>
            <span>{formatHeaderTime()}</span>
            <span>AEDT</span>
          </div>
        </header>

        <main className="eiq-approved-shell__content">{children}</main>

        <footer className="eiq-approved-shell__footer">
          <span>EDGEiQ Racing Intelligence Operating System</span>
          <span>Build: 1.0.0</span>
          <span>Data as at: {formatHeaderTime()} AEDT</span>
        </footer>
      </div>
    </section>
  );
}
"""
    write(path, text)


def write_css() -> None:
    path = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
    css = r""":root {
  --eiq-approved-bg: #ffffff;
  --eiq-approved-page: #f7f9fc;
  --eiq-approved-surface: #ffffff;
  --eiq-approved-surface-soft: #f8fafc;
  --eiq-approved-line: #dde5ef;
  --eiq-approved-line-strong: #c8d3df;
  --eiq-approved-blue: #0759d7;
  --eiq-approved-blue-soft: #edf4ff;
  --eiq-approved-blue-mid: #dbeaff;
  --eiq-approved-navy: #091a44;
  --eiq-approved-text: #0d1b3d;
  --eiq-approved-muted: #52637f;
  --eiq-approved-faint: #75849a;
  --eiq-approved-green: #17a34a;
  --eiq-approved-red: #cc3340;
  --eiq-approved-amber: #c78a00;
  --eiq-approved-sidebar: 240px;
  color-scheme: light;
}

html,
body,
#root {
  min-height: 100%;
  margin: 0;
  background: #ffffff !important;
  color: var(--eiq-approved-text) !important;
  color-scheme: light !important;
  font-family: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.eiq-approved-shell,
.eiq-approved-shell * {
  box-sizing: border-box;
}

.eiq-approved-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: var(--eiq-approved-sidebar) minmax(0, 1fr);
  background: #ffffff;
  color: var(--eiq-approved-text);
  font-feature-settings: "tnum" 1, "lnum" 1;
}

.eiq-app-nav {
  width: var(--eiq-approved-sidebar);
  min-height: 100vh;
  position: sticky;
  top: 0;
  align-self: start;
  background: #ffffff !important;
  border-right: 1px solid var(--eiq-approved-line);
  padding: 20px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.eiq-app-nav__brand {
  height: 66px;
  border-bottom: 1px solid var(--eiq-approved-line);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.eiq-app-nav__brand strong {
  color: var(--eiq-approved-blue);
  font-size: 36px;
  line-height: 0.92;
  font-weight: 900;
  letter-spacing: -0.07em;
}

.eiq-app-nav__brand strong span {
  color: #0aa0d8;
}

.eiq-app-nav__brand em {
  margin-top: 5px;
  color: var(--eiq-approved-navy);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-app-nav nav {
  display: grid;
  gap: 3px;
}

.eiq-app-nav button {
  min-height: 38px;
  width: 100%;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--eiq-approved-navy);
  padding: 0 12px;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.eiq-app-nav button span {
  width: 21px;
  height: 21px;
  display: grid;
  place-items: center;
  border: 1.4px solid currentColor;
  border-radius: 4px;
  color: #18315e;
  font-size: 10px;
  font-weight: 900;
  line-height: 1;
}

.eiq-app-nav button strong {
  color: inherit;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.eiq-app-nav button.is-active,
.eiq-app-nav button:hover {
  background: var(--eiq-approved-blue-soft);
  color: var(--eiq-approved-blue);
}

.eiq-app-nav button.is-active span,
.eiq-app-nav button:hover span {
  color: var(--eiq-approved-blue);
}

.eiq-app-nav button:nth-child(12) {
  margin-top: 14px;
  border-top: 1px solid var(--eiq-approved-line);
  padding-top: 8px;
}

.eiq-approved-shell__frame {
  min-width: 0;
  min-height: 100vh;
  display: grid;
  grid-template-rows: 84px minmax(0, 1fr) 52px;
  background: #ffffff;
}

.eiq-approved-topbar {
  border-bottom: 1px solid var(--eiq-approved-line);
  background: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 0 24px 0 20px;
}

.eiq-approved-topbar__identity strong {
  display: block;
  color: var(--eiq-approved-navy);
  font-size: 20px;
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: 0.01em;
}

.eiq-approved-topbar__identity span {
  display: block;
  margin-top: 6px;
  color: var(--eiq-approved-muted);
  font-size: 14px;
}

.eiq-approved-topbar__ops {
  display: flex;
  align-items: center;
  gap: 18px;
  color: var(--eiq-approved-navy);
  font-size: 13px;
  white-space: nowrap;
}

.eiq-approved-topbar__ops span {
  border-left: 1px solid var(--eiq-approved-line);
  padding-left: 18px;
}

.eiq-approved-topbar__ops span:first-child {
  border-left: 0;
  padding-left: 0;
}

.eiq-approved-shell__content {
  min-width: 0;
  width: 100%;
  padding: 32px 24px 18px 18px;
  background: #ffffff;
  overflow: auto;
}

.eiq-approved-shell__footer {
  border-top: 1px solid var(--eiq-approved-line);
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 24px;
  color: var(--eiq-approved-muted);
  font-size: 12px;
}

.eiq-approved-table {
  width: 100%;
  border-collapse: collapse;
  color: var(--eiq-approved-text);
  background: #ffffff;
  font-size: 13px;
}

.eiq-approved-table th {
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--eiq-approved-line);
  background: var(--eiq-approved-surface-soft);
  color: var(--eiq-approved-navy);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  text-align: left;
  white-space: nowrap;
}

.eiq-approved-table td {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--eiq-approved-line);
  color: var(--eiq-approved-text);
  vertical-align: middle;
}

.eiq-approved-table strong {
  color: var(--eiq-approved-navy);
  font-weight: 800;
}

.eiq-approved-table small {
  display: block;
  margin-top: 2px;
  color: var(--eiq-approved-muted);
  font-size: 11px;
}

.eiq-approved-button {
  height: 34px;
  border: 1px solid var(--eiq-approved-blue);
  border-radius: 4px;
  background: #ffffff;
  color: var(--eiq-approved-blue);
  padding: 0 14px;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.eiq-approved-pill {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  border-radius: 6px;
  background: #dff6e6;
  color: #167239;
  padding: 0 13px;
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 980px) {
  .eiq-approved-shell {
    grid-template-columns: 1fr;
  }

  .eiq-app-nav {
    position: relative;
    width: 100%;
    min-height: auto;
  }

  .eiq-approved-shell__frame {
    grid-template-rows: auto minmax(0, 1fr) auto;
  }
}
"""
    write(path, css)


def main() -> None:
    paths = [
        ROOT / "src" / "main.tsx",
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "WorkspaceShell.tsx",
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "AppNavigation.tsx",
        ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css",
    ]
    checkpoint(paths)
    patch_main()
    patch_app_navigation()
    patch_workspace_shell()
    write_css()
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE02_SHELL_PASS")


if __name__ == "__main__":
    main()
