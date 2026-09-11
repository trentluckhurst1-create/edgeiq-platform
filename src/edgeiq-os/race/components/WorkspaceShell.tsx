import type { ReactNode } from "react";
import { AppNavigation, type GlobalSection } from "./AppNavigation";

type WorkspaceShellProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
  children: ReactNode;
};

function formatHeaderDate() {
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }).format(new Date()).toUpperCase();
}

function formatHeaderTime() {
  return new Intl.DateTimeFormat("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
}

export function WorkspaceShell({ activeSection, onSectionChange, children }: WorkspaceShellProps) {
  return (
    <section className={`eiq-approved-shell is-${activeSection}${activeSection === "home" ? " is-dashboard" : " is-meetings"}`} data-edgeiq-approved-ui="dashboard-meetings-baseline" data-edgeiq-active-section={activeSection}>
      <AppNavigation activeSection={activeSection} onSectionChange={onSectionChange} />
      <div className="eiq-approved-shell__frame">
        <header className="eiq-approved-topbar">
          <div className="eiq-approved-topbar__identity"><span className="eiq-approved-topbar__product">EDGEiQ / RACING</span></div>
          <div className="eiq-approved-topbar__ops" aria-label="Operational context">
            <span className="eiq-approved-topbar__status"><i aria-hidden="true" /> LIVE</span>
            <span>{formatHeaderDate()}</span>
            <span>{formatHeaderTime()} AEDT</span>
          </div>
        </header>
        <main className="eiq-approved-shell__content"><div className="eiq-workspace-stage">{children}</div></main>
        <footer className="eiq-approved-shell__footer"><span>EDGEiQ Racing Intelligence</span><span>Dashboard · Meetings</span><span>{formatHeaderTime()} AEDT</span></footer>
      </div>
    </section>
  );
}
