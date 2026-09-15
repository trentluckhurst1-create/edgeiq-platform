import type { ReactNode } from "react";
import { AppNavigation, type GlobalSection } from "./AppNavigation";

type WorkspaceShellProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
  children: ReactNode;
};

const MELBOURNE_TIME_ZONE = "Australia/Melbourne";

function formatHeaderDate() {
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "2-digit", month: "short", year: "numeric", timeZone: MELBOURNE_TIME_ZONE }).format(new Date()).toUpperCase();
}

function formatHeaderTime() {
  return new Intl.DateTimeFormat("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: MELBOURNE_TIME_ZONE }).format(new Date());
}

function formatTimeZone() {
  const parts = new Intl.DateTimeFormat("en-AU", { timeZone: MELBOURNE_TIME_ZONE, timeZoneName: "short" }).formatToParts(new Date());
  return parts.find((part) => part.type === "timeZoneName")?.value ?? "AET";
}

const workspaceLabels: Partial<Record<GlobalSection, string>> = {
  home: "Dashboard",
  meetings: "Meetings",
  race: "Race",
  field: "Field",
  formGuide: "Form",
  performance: "Performance",
  epi: "Nexus",
  map: "Map",
  market: "Market",
  results: "Results",
  track: "Track",
  weather: "Weather",
  overview: "Overview",
  insights: "Insights",
};

export function WorkspaceShell({ activeSection, onSectionChange, children }: WorkspaceShellProps) {
  const label = workspaceLabels[activeSection] ?? "EDGEiQ";
  const workspaceTrail = activeSection === "home" ? "Dashboard" : activeSection === "meetings" ? "Dashboard · Meetings" : `Dashboard · Meetings · ${label}`;
  const zone = formatTimeZone();

  return (
    <section className={`eiq-approved-shell is-${activeSection}${activeSection === "home" ? " is-dashboard" : activeSection === "meetings" ? " is-meetings" : ""}`} data-edgeiq-approved-ui="locked-2026-09-15" data-edgeiq-active-section={activeSection}>
      <AppNavigation activeSection={activeSection} onSectionChange={onSectionChange} />
      <div className="eiq-approved-shell__frame">
        <header className="eiq-approved-topbar">
          <div className="eiq-approved-topbar__identity"><span className="eiq-approved-topbar__product">EDGEiQ / RACING</span></div>
          <div className="eiq-approved-topbar__ops" aria-label="Operational context">
            <span className="eiq-approved-topbar__status"><i aria-hidden="true" /> LIVE</span>
            <span>{formatHeaderDate()}</span>
            <span>{formatHeaderTime()} {zone}</span>
          </div>
        </header>
        <main className="eiq-approved-shell__content">
          <div className="eiq-workspace-stage">{children}</div>
        </main>
        <footer className="eiq-approved-shell__footer"><span>EDGEiQ Racing Intelligence</span><span>{workspaceTrail}</span><span>{formatHeaderTime()} {zone}</span></footer>
      </div>
    </section>
  );
}
