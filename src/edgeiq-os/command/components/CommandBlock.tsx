import type { ReactNode } from "react";

type CommandBlockProps = {
  title: string;
  updated?: string;
  tone?: "blue" | "amber" | "green" | "purple" | "assessment";
  children: ReactNode;
};

export function CommandBlock({ title, updated, tone = "blue", children }: CommandBlockProps) {
  return (
    <article className={`eiq-command-block is-${tone}`}>
      <header>
        <span>{title}</span>
        {updated ? <small>{updated} · LIVE</small> : null}
      </header>
      {children}
    </article>
  );
}
