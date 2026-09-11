import type { ReactNode } from "react";
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
    hour12: false,
  }).format(new Date());
}

export function WorkspaceShell({
  activeSection,
  onSectionChange,
  eyebrow,
  title,
  meta,
  children,
}: WorkspaceShellProps) {
  const ownsPageHeader = activeSection === "home" || activeSection === "meetings";

  return (
    <section className={`eiq-approved-shell${activeSection === "home" ? " is-dashboard" : ""}${activeSection === "meetings" ? " is-meetings" : ""}`} data-edgeiq-approved-ui="v2">
      <AppNavigation activeSection={activeSection} onSectionChange={onSectionChange} />

      <div className="eiq-approved-shell__frame">
        <header className="eiq-approved-topbar">
          <div className="eiq-approved-topbar__identity">
            <span className="eiq-approved-topbar__product">EDGEiQ / RACING</span>
            {!ownsPageHeader ? <strong>{title}</strong> : null}
          </div>
          <div className="eiq-approved-topbar__ops" aria-label="Operational context">
            <span className="eiq-approved-topbar__status"><i aria-hidden="true" /> LIVE</span>
            <span>{formatHeaderDate()}</span>
            <span>{formatHeaderTime()} AEDT</span>
          </div>
        </header>

        <main className="eiq-approved-shell__content">
          {!ownsPageHeader ? (
            <header className="eiq-workspace-masthead">
              <div className="eiq-workspace-masthead__copy">
                <span className="eiq-workspace-masthead__eyebrow">{eyebrow}</span>
                <div className="eiq-workspace-masthead__title-row">
                  <h1>{title}</h1>
                  <span className="eiq-workspace-masthead__mode">PRO WORKSPACE</span>
                </div>
                {meta ? <p>{meta}</p> : null}
              </div>
              <div className="eiq-workspace-masthead__status" aria-label="EDGEiQ system status">
                <span>DATA STATUS</span>
                <strong><i className="eiq-system-dot" aria-hidden="true" /> CURRENT</strong>
              </div>
            </header>
          ) : null}
          <div className="eiq-workspace-stage">{children}</div>
        </main>

        <footer className="eiq-approved-shell__footer">
          <span>EDGEiQ Racing Intelligence</span>
          <span>Form · Ratings · Map · Market</span>
          <span>{formatHeaderTime()} AEDT</span>
        </footer>
      </div>
    </section>
  );
}