import { ReactNode, useEffect, useMemo, useState } from "react";
import { EdgeiqWorkspace, useEdgeiqOs } from "../../state/edgeiqOsStore";
import "./edgeiqOsShell.css";

type EdgeiqTheme = "dark" | "light";

type EdgeiqOsShellProps = {
  children: ReactNode;
  activeSection?: string;
  activeWorkspace?: string;
  meetingName?: string;
  raceLabel?: string;
  distanceLabel?: string;
  trackLabel?: string;
  railLabel?: string;
  statusLabel?: string;
};

export function EdgeiqOsShell({
  children,
  activeSection = "RACES",
  activeWorkspace = "COMMAND",
  meetingName = "Current",
  raceLabel = "Selected",
  distanceLabel = "Distance",
  trackLabel = "Live",
  railLabel = "Context",
  statusLabel = "LIVE",
}: EdgeiqOsShellProps) {
  const [theme, setTheme] = useState<EdgeiqTheme>(() => {
    const stored = window.localStorage.getItem("edgeiq-theme");
    return stored === "light" ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-edgeiq-theme", theme);
    window.localStorage.setItem("edgeiq-theme", theme);
  }, [theme]);

  const nextTheme = useMemo(() => (theme === "dark" ? "light" : "dark"), [theme]);
  const os = useEdgeiqOs();
  const toolbarContext = os.raceContext;

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
          <button className={`edgeiq-os__nav-item ${os.activeSection === "HOME" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("HOME")}>HOME</button>
          <button className={`edgeiq-os__nav-item ${os.activeSection === "TODAY" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("TODAY")}>TODAY</button>

          <div className="edgeiq-os__nav-group">
            <div className="edgeiq-os__nav-label">RACES</div>
            {(["COMMAND", "FIELD", "MAP", "MARKET", "PERFORMANCE", "CONDITIONS"] as EdgeiqWorkspace[]).map((workspace) => (
              <button
                key={workspace}
                className={`edgeiq-os__nav-sub ${os.activeSection === "RACES" && os.activeWorkspace === workspace ? "is-active" : ""}`}
                type="button"
                onClick={() => {
                  os.setActiveSection("RACES");
                  os.setActiveWorkspace(workspace);
                }}
              >
                {workspace}
              </button>
            ))}
          </div>

          <button className={`edgeiq-os__nav-item ${os.activeSection === "RESULTS" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("RESULTS")}>RESULTS</button>
          <button className={`edgeiq-os__nav-item ${os.activeSection === "LAB" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("LAB")}>LAB</button>
          <button className={`edgeiq-os__nav-item ${os.activeSection === "SETTINGS" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("SETTINGS")}>SETTINGS</button>
        </nav>
      </aside>

      <main className="edgeiq-os__main">
        <header className="edgeiq-os__toolbar">
          <div className="edgeiq-os__context">
            <span>Meeting</span>
            <strong>{toolbarContext.meeting || meetingName}</strong>
            <span>Race</span>
            <strong>{toolbarContext.race || raceLabel}</strong>
            <span>Distance</span>
            <strong>{toolbarContext.distance || distanceLabel}</strong>
            <span>Track</span>
            <strong>{toolbarContext.track || trackLabel}</strong>
            <span>Rail</span>
            <strong>{toolbarContext.rail || railLabel}</strong>
            <span>Jump</span>
            <strong>{toolbarContext.jump || "Pending"}</strong>
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
          <span>DATA: {statusLabel}</span>
          <span>INTELLIGENCE: ONLINE</span>
          <span>PRICING: AVAILABLE</span>
          <span>EDGEiQ OS: SPRINT 1</span>
        </footer>
      </main>
    </div>
  );
}
