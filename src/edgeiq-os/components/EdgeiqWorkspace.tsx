import type { ReactNode } from "react";

type EdgeiqWorkspaceProps = {
  title: string;
  eyebrow?: string;
  meta?: string;
  timeline?: string[];
  children: ReactNode;
  operationalRail?: ReactNode;
};

export function EdgeiqWorkspace({
  title,
  eyebrow,
  meta,
  timeline = [],
  children,
  operationalRail,
}: EdgeiqWorkspaceProps) {
  return (
    <section className="eiq-workspace">
      <div className="eiq-workspace__main">
        <header className="eiq-workspace__header">
          {eyebrow ? <span>{eyebrow}</span> : null}
          <h1>{title}</h1>
          {meta ? <p>{meta}</p> : null}
        </header>

        <div className="eiq-workspace__body">
          {timeline.length ? (
            <aside className="eiq-timeline" aria-label="Workspace timeline">
              {timeline.map((item, index) => (
                <div className={index === 0 ? "eiq-timeline__item is-active" : "eiq-timeline__item"} key={item}>
                  <b>{String(index + 1).padStart(2, "0")}</b>
                  <span>{item}</span>
                </div>
              ))}
            </aside>
          ) : null}

          <div className="eiq-workspace__content">{children}</div>
        </div>
      </div>

      {operationalRail ? <aside className="eiq-operational-rail">{operationalRail}</aside> : null}
    </section>
  );
}
