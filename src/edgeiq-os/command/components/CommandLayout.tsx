
import type { ReactNode } from "react";

type CommandLayoutProps = {
  header: ReactNode;
  alerts: ReactNode;
  brief: ReactNode;
  decision: ReactNode;
  operations: ReactNode;
  findings: ReactNode;
  explorer: ReactNode;
  inbox: ReactNode;
  drawer: ReactNode;
  rail: ReactNode;
};

export function CommandLayout({
  header,
  alerts,
  brief,
  decision,
  operations,
  findings,
  explorer,
  inbox,
  drawer,
  rail,
}: CommandLayoutProps) {
  return (
    <section className="eiq-command-v3">
      <main className="eiq-command-v3__main">
        {header}
        {alerts}

        <section className="eiq-command-v3__grid">
          <div className="eiq-command-v3__primary">
            {brief}
            {decision}
            {operations}
            {findings}
            {explorer}
          </div>

          <div className="eiq-command-v3__activity">
            {inbox}
          </div>

          {drawer}
          {rail}
        </section>
      </main>
    </section>
  );
}
