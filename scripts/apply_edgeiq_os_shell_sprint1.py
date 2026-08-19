from pathlib import Path
from datetime import datetime

root = Path.cwd()
src = root / "src"

files = {
"src/components/shell/EdgeiqOsShell.tsx": r'''import { ReactNode, useEffect, useMemo, useState } from "react";
import "./edgeiqOsShell.css";

type EdgeiqTheme = "dark" | "light";

type EdgeiqOsShellProps = {
  children: ReactNode;
};

export function EdgeiqOsShell({ children }: EdgeiqOsShellProps) {
  const [theme, setTheme] = useState<EdgeiqTheme>(() => {
    const stored = window.localStorage.getItem("edgeiq-theme");
    return stored === "light" ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-edgeiq-theme", theme);
    window.localStorage.setItem("edgeiq-theme", theme);
  }, [theme]);

  const nextTheme = useMemo(() => (theme === "dark" ? "light" : "dark"), [theme]);

  return (
    <div className="edgeiq-os">
      <aside className="edgeiq-os__nav">
        <div className="edgeiq-os__brand">
          <div className="edgeiq-os__mark">E</div>
          <div>
            <div className="edgeiq-os__brand-name">EDGEiQ OS</div>
            <div className="edgeiq-os__brand-sub">Racing Intelligence</div>
          </div>
        </div>

        <nav className="edgeiq-os__nav-list">
          <button className="edgeiq-os__nav-item is-active">HOME</button>
          <button className="edgeiq-os__nav-item">TODAY</button>

          <div className="edgeiq-os__nav-group">
            <div className="edgeiq-os__nav-label">RACES</div>
            <button className="edgeiq-os__nav-sub is-active">COMMAND</button>
            <button className="edgeiq-os__nav-sub">FIELD</button>
            <button className="edgeiq-os__nav-sub">MAP</button>
            <button className="edgeiq-os__nav-sub">MARKET</button>
            <button className="edgeiq-os__nav-sub">PERFORMANCE</button>
            <button className="edgeiq-os__nav-sub">CONDITIONS</button>
          </div>

          <button className="edgeiq-os__nav-item">RESULTS</button>
          <button className="edgeiq-os__nav-item">LAB</button>
          <button className="edgeiq-os__nav-item">SETTINGS</button>
        </nav>
      </aside>

      <main className="edgeiq-os__main">
        <header className="edgeiq-os__toolbar">
          <div className="edgeiq-os__context">
            <span>Meeting</span>
            <strong>Current</strong>
            <span>Race</span>
            <strong>Selected</strong>
            <span>Track</span>
            <strong>Live</strong>
            <span>Rail</span>
            <strong>Context</strong>
          </div>

          <div className="edgeiq-os__actions">
            <button
              className="edgeiq-os__theme"
              type="button"
              onClick={() => setTheme(nextTheme)}
              aria-label={`Switch to ${nextTheme} mode`}
            >
              {theme === "dark" ? "☀" : "🌙"}
            </button>
            <button className="edgeiq-os__tool" type="button">Notes</button>
            <button className="edgeiq-os__user" type="button">User</button>
          </div>
        </header>

        <section className="edgeiq-os__workspace">
          {children}
        </section>

        <footer className="edgeiq-os__status">
          <span>DATA: LIVE</span>
          <span>INTELLIGENCE: ONLINE</span>
          <span>PRICING: AVAILABLE</span>
          <span>EDGEiQ OS: SPRINT 1</span>
        </footer>
      </main>
    </div>
  );
}
''',

"src/components/shell/index.ts": r'''export { EdgeiqOsShell } from "./EdgeiqOsShell";
''',

"src/components/shell/edgeiqOsShell.css": r''':root {
  --edgeiq-bg: #080a0f;
  --edgeiq-bg-secondary: #0d1118;
  --edgeiq-panel: #101620;
  --edgeiq-panel-elevated: #151d29;
  --edgeiq-border: rgba(255, 255, 255, 0.1);
  --edgeiq-border-muted: rgba(255, 255, 255, 0.06);
  --edgeiq-text: #f4f7fb;
  --edgeiq-text-secondary: #c6cfda;
  --edgeiq-text-muted: #7e8897;
  --edgeiq-success: #33d17a;
  --edgeiq-warning: #f7c948;
  --edgeiq-danger: #ff5c5c;
  --edgeiq-info: #70a7ff;
  --edgeiq-accent: #d8b86a;
  --edgeiq-sidebar-width: 248px;
  --edgeiq-toolbar-height: 64px;
  --edgeiq-status-height: 34px;
}

:root[data-edgeiq-theme="light"] {
  --edgeiq-bg: #f4f5f7;
  --edgeiq-bg-secondary: #ffffff;
  --edgeiq-panel: #ffffff;
  --edgeiq-panel-elevated: #f8f9fb;
  --edgeiq-border: rgba(14, 20, 30, 0.12);
  --edgeiq-border-muted: rgba(14, 20, 30, 0.07);
  --edgeiq-text: #121722;
  --edgeiq-text-secondary: #364050;
  --edgeiq-text-muted: #697386;
  --edgeiq-success: #128447;
  --edgeiq-warning: #9b6a00;
  --edgeiq-danger: #c73737;
  --edgeiq-info: #245fbd;
  --edgeiq-accent: #8b6f25;
}

.edgeiq-os {
  min-height: 100vh;
  display: grid;
  grid-template-columns: var(--edgeiq-sidebar-width) minmax(0, 1fr);
  background: var(--edgeiq-bg);
  color: var(--edgeiq-text);
}

.edgeiq-os * {
  box-sizing: border-box;
}

.edgeiq-os__nav {
  border-right: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-bg-secondary);
  padding: 22px 18px;
}

.edgeiq-os__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 34px;
}

.edgeiq-os__mark {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-panel);
  color: var(--edgeiq-accent);
  font-weight: 800;
  letter-spacing: 0.08em;
}

.edgeiq-os__brand-name {
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.edgeiq-os__brand-sub {
  margin-top: 3px;
  font-size: 11px;
  color: var(--edgeiq-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.edgeiq-os__nav-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.edgeiq-os__nav-item,
.edgeiq-os__nav-sub {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--edgeiq-text-secondary);
  text-align: left;
  cursor: pointer;
  font: inherit;
  letter-spacing: 0.08em;
}

.edgeiq-os__nav-item {
  padding: 12px 12px;
  font-size: 12px;
  font-weight: 700;
}

.edgeiq-os__nav-sub {
  padding: 9px 12px 9px 22px;
  font-size: 11px;
  color: var(--edgeiq-text-muted);
}

.edgeiq-os__nav-item.is-active,
.edgeiq-os__nav-sub.is-active {
  background: var(--edgeiq-panel-elevated);
  color: var(--edgeiq-text);
  border-left: 2px solid var(--edgeiq-accent);
}

.edgeiq-os__nav-label {
  margin: 16px 0 8px 12px;
  color: var(--edgeiq-text-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.edgeiq-os__main {
  min-width: 0;
  display: grid;
  grid-template-rows: var(--edgeiq-toolbar-height) minmax(0, 1fr) var(--edgeiq-status-height);
}

.edgeiq-os__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-bg-secondary);
  padding: 0 22px;
}

.edgeiq-os__context {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  white-space: nowrap;
}

.edgeiq-os__context span {
  color: var(--edgeiq-text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.edgeiq-os__context strong {
  color: var(--edgeiq-text);
  font-size: 12px;
  font-weight: 800;
  margin-right: 12px;
}

.edgeiq-os__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edgeiq-os__theme,
.edgeiq-os__tool,
.edgeiq-os__user {
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-panel);
  color: var(--edgeiq-text);
  height: 34px;
  padding: 0 12px;
  cursor: pointer;
}

.edgeiq-os__workspace {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  background: var(--edgeiq-bg);
}

.edgeiq-os__status {
  display: flex;
  align-items: center;
  gap: 18px;
  border-top: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-bg-secondary);
  color: var(--edgeiq-text-muted);
  padding: 0 18px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  white-space: nowrap;
}

@media (max-width: 980px) {
  .edgeiq-os {
    grid-template-columns: 1fr;
  }

  .edgeiq-os__nav {
    display: none;
  }

  .edgeiq-os__context {
    overflow: auto;
  }
}
'''
}

for file, content in files.items():
    path = root / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

main = src / "main.tsx"
if main.exists():
    text = main.read_text(encoding="utf-8")
    if 'components/shell/edgeiqOsShell.css' not in text:
        text = 'import "./components/shell/edgeiqOsShell.css";\n' + text
        main.write_text(text, encoding="utf-8")

app = src / "App.tsx"
if not app.exists():
    raise SystemExit("src/App.tsx not found")

text = app.read_text(encoding="utf-8")
checkpoint = app.with_name(f"App_CHECKPOINT_BEFORE_EDGEIQ_OS_SHELL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsx")
checkpoint.write_text(text, encoding="utf-8")

if 'components/shell' not in text:
    text = 'import { EdgeiqOsShell } from "./components/shell";\n' + text

if '<EdgeiqOsShell>' not in text:
    text = text.replace('<RaceIntelligenceScreen />', '<EdgeiqOsShell><RaceIntelligenceScreen /></EdgeiqOsShell>')

app.write_text(text, encoding="utf-8")

print("[EDGEIQ_OS_SHELL_SPRINT_1] shell files created")
print("[EDGEIQ_OS_SHELL_SPRINT_1] App.tsx checkpoint created")
print("[EDGEIQ_OS_SHELL_SPRINT_1] App.tsx wrapped if RaceIntelligenceScreen pattern matched")
