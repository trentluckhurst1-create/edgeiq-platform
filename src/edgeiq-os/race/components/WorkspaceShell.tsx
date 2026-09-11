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
    hour12: true,
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
  return (
    <section className="eiq-approved-shell" data-edgeiq-approved-ui="v1">
      <AppNavigation activeSection={activeSection} onSectionChange={onSectionChange} />

      <div className="eiq-approved-shell__frame">
        <header className="eiq-approved-topbar">
          <div className="eiq-approved-topbar__identity">
            <strong>EDGEiQ RACING</strong>
            <span>Professional Form · Ratings · Maps · Pricing</span>
          </div>
          <div className="eiq-approved-topbar__ops" aria-label="Operational context">
            <span>{formatHeaderDate()}</span>
            <span>{formatHeaderTime()}</span>
            <span>AEDT</span>
          </div>
        </header>

        <main className="eiq-approved-shell__content">
          <header className="eiq-workspace-masthead">
            <div>
              <span className="eiq-workspace-masthead__eyebrow">{eyebrow}</span>
              <h1>{title}</h1>
              {meta ? <p>{meta}</p> : null}
            </div>
            <div className="eiq-workspace-masthead__status" aria-label="EDGEiQ system status">
              <span className="eiq-system-dot" aria-hidden="true" />
              <strong>LIVE WORKSPACE</strong>
            </div>
          </header>
          <div className="eiq-workspace-stage">{children}</div>
        </main>

        <footer className="eiq-approved-shell__footer">
          <span>EDGEiQ Racing Intelligence</span>
          <span>Form · Ratings · Map · Market</span>
          <span>Data as at {formatHeaderTime()} AEDT</span>
        </footer>
      </div>
    </section>
  );
}
