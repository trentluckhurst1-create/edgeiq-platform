import React from "react";

type Tone = "neutral" | "accent" | "positive" | "warning" | "risk";

const toneClass: Record<Tone, string> = {
  neutral: "edgeiq-ui-neutral",
  accent: "edgeiq-ui-accent",
  positive: "edgeiq-ui-positive",
  warning: "edgeiq-ui-warning",
  risk: "edgeiq-ui-risk",
};

export function EdgeiqBadge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={`edgeiq-ui-badge ${toneClass[tone]}`}>{children}</span>;
}

export function EdgeiqEmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="edgeiq-empty-state">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

export function EdgeiqSourceBlocker({ children }: { children: React.ReactNode }) {
  return <div className="edgeiq-source-blocker">{children}</div>;
}
