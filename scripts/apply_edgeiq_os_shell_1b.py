from pathlib import Path

root = Path.cwd()
shell = root / "src" / "components" / "shell" / "EdgeiqOsShell.tsx"

text = shell.read_text(encoding="utf-8")

text = text.replace(
'''type EdgeiqOsShellProps = {
  children: ReactNode;
};''',
'''type EdgeiqOsShellProps = {
  children: ReactNode;
  activeSection?: string;
  activeWorkspace?: string;
  meetingName?: string;
  raceLabel?: string;
  distanceLabel?: string;
  trackLabel?: string;
  railLabel?: string;
  statusLabel?: string;
};'''
)

text = text.replace(
'''export function EdgeiqOsShell({ children }: EdgeiqOsShellProps) {''',
'''export function EdgeiqOsShell({
  children,
  activeSection = "RACES",
  activeWorkspace = "COMMAND",
  meetingName = "Current",
  raceLabel = "Selected",
  distanceLabel = "Distance",
  trackLabel = "Live",
  railLabel = "Context",
  statusLabel = "LIVE",
}: EdgeiqOsShellProps) {'''
)

text = text.replace(
'''          <button className="edgeiq-os__nav-item is-active">HOME</button>
          <button className="edgeiq-os__nav-item">TODAY</button>''',
'''          <button className={`edgeiq-os__nav-item ${activeSection === "HOME" ? "is-active" : ""}`}>HOME</button>
          <button className={`edgeiq-os__nav-item ${activeSection === "TODAY" ? "is-active" : ""}`}>TODAY</button>'''
)

text = text.replace(
'''            <button className="edgeiq-os__nav-sub is-active">COMMAND</button>
            <button className="edgeiq-os__nav-sub">FIELD</button>
            <button className="edgeiq-os__nav-sub">MAP</button>
            <button className="edgeiq-os__nav-sub">MARKET</button>
            <button className="edgeiq-os__nav-sub">PERFORMANCE</button>
            <button className="edgeiq-os__nav-sub">CONDITIONS</button>''',
'''            {["COMMAND", "FIELD", "MAP", "MARKET", "PERFORMANCE", "CONDITIONS"].map((workspace) => (
              <button
                key={workspace}
                className={`edgeiq-os__nav-sub ${activeWorkspace === workspace ? "is-active" : ""}`}
                type="button"
              >
                {workspace}
              </button>
            ))}'''
)

text = text.replace(
'''          <button className="edgeiq-os__nav-item">RESULTS</button>
          <button className="edgeiq-os__nav-item">LAB</button>
          <button className="edgeiq-os__nav-item">SETTINGS</button>''',
'''          <button className={`edgeiq-os__nav-item ${activeSection === "RESULTS" ? "is-active" : ""}`}>RESULTS</button>
          <button className={`edgeiq-os__nav-item ${activeSection === "LAB" ? "is-active" : ""}`}>LAB</button>
          <button className={`edgeiq-os__nav-item ${activeSection === "SETTINGS" ? "is-active" : ""}`}>SETTINGS</button>'''
)

text = text.replace(
'''            <span>Meeting</span>
            <strong>Current</strong>
            <span>Race</span>
            <strong>Selected</strong>
            <span>Track</span>
            <strong>Live</strong>
            <span>Rail</span>
            <strong>Context</strong>''',
'''            <span>Meeting</span>
            <strong>{meetingName}</strong>
            <span>Race</span>
            <strong>{raceLabel}</strong>
            <span>Distance</span>
            <strong>{distanceLabel}</strong>
            <span>Track</span>
            <strong>{trackLabel}</strong>
            <span>Rail</span>
            <strong>{railLabel}</strong>'''
)

text = text.replace(
'''          <span>DATA: LIVE</span>''',
'''          <span>DATA: {statusLabel}</span>'''
)

shell.write_text(text, encoding="utf-8")
print("[EDGEIQ_OS_SHELL_1B] shell props/state wiring added")
