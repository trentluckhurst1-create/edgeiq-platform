from pathlib import Path

base = Path("src/edgeiq-os/design-system")
tokens = base / "tokens"
formatters = base / "formatters"
components = base / "components"

for path in [tokens, formatters, components]:
    path.mkdir(parents=True, exist_ok=True)

(tokens / "typography.ts").write_text('''
export const edgeiqTypography = {
  display: "eiq-ds-display",
  title: "eiq-ds-title",
  section: "eiq-ds-section",
  label: "eiq-ds-label",
  body: "eiq-ds-body",
};
'''.lstrip(), encoding="utf-8")

(tokens / "spacing.ts").write_text('''
export const edgeiqSpacing = {
  xs: "4px",
  sm: "8px",
  md: "12px",
  lg: "18px",
  xl: "28px",
  xxl: "40px",
  xxxl: "64px",
};
'''.lstrip(), encoding="utf-8")

(tokens / "colours.ts").write_text('''
export const edgeiqColours = {
  surface: "#080806",
  surfaceRaised: "rgba(255,255,255,0.035)",
  surfaceHover: "rgba(255,255,255,0.065)",
  textPrimary: "#f6f3ea",
  textSecondary: "rgba(246,243,234,0.72)",
  textMuted: "rgba(246,243,234,0.48)",
  divider: "rgba(246,243,234,0.10)",
  success: "#7edc9b",
  warning: "#e6bf69",
  critical: "#ef6b6b",
};
'''.lstrip(), encoding="utf-8")

(tokens / "motion.ts").write_text('''
export const edgeiqMotion = {
  fast: "120ms",
  normal: "180ms",
  slow: "280ms",
  ease: "cubic-bezier(0.2, 0.8, 0.2, 1)",
};
'''.lstrip(), encoding="utf-8")

(tokens / "radius.ts").write_text('''
export const edgeiqRadius = {
  sm: "10px",
  md: "16px",
  lg: "24px",
  pill: "999px",
};
'''.lstrip(), encoding="utf-8")

(formatters / "statusFormatter.ts").write_text('''
export function formatIntelligenceStatus(status: string): string {
  if (status === "READY") return "Assessment Complete";
  if (status === "PARTIAL") return "Building Assessment";
  if (status === "PLACEHOLDER") return "Awaiting Intelligence";
  if (status === "ERROR") return "Intelligence Unavailable";
  return status;
}
'''.lstrip(), encoding="utf-8")

(formatters / "confidenceFormatter.ts").write_text('''
export function formatConfidenceLabel(confidence: number): string {
  if (confidence >= 85) return "Very High";
  if (confidence >= 70) return "High";
  if (confidence >= 55) return "Moderate";
  if (confidence >= 40) return "Developing";
  return "Low";
}
'''.lstrip(), encoding="utf-8")

(formatters / "decisionFormatter.ts").write_text('''
export function formatDecisionState(decision: string): string {
  if (decision === "EXECUTE") return "Escalate";
  if (decision === "MONITOR") return "Maintain Monitoring";
  if (decision === "WAIT") return "Wait";
  if (decision === "REVIEW") return "Review Required";
  return decision;
}
'''.lstrip(), encoding="utf-8")

(formatters / "priorityFormatter.ts").write_text('''
export function formatPriority(priority: string): string {
  if (priority === "CRITICAL") return "Critical Watch";
  if (priority === "HIGH") return "High Attention";
  if (priority === "NORMAL") return "Routine Monitoring";
  if (priority === "LOW") return "Low Attention";
  return priority;
}
'''.lstrip(), encoding="utf-8")

(formatters / "narrativeFormatter.ts").write_text('''
export type EdgeiqNarrative = {
  currentView: string;
  whyItMatters: string;
  watch: string;
  recommendedAction?: string;
};

export function buildBasicNarrative(input: {
  title: string;
  summary: string;
  status?: string;
  confidence?: number;
}): EdgeiqNarrative {
  return {
    currentView: input.summary,
    whyItMatters: `${input.title} is contributing to the current assessment.`,
    watch: input.status === "READY"
      ? "Continue monitoring for any material change."
      : "This area is still developing and should not be treated as final.",
  };
}
'''.lstrip(), encoding="utf-8")

(components / "StatusBadge.tsx").write_text('''
import { formatIntelligenceStatus } from "../formatters/statusFormatter";

type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`eiq-ds-status eiq-ds-status--${status.toLowerCase()}`}>{formatIntelligenceStatus(status)}</span>;
}
'''.lstrip(), encoding="utf-8")

(components / "SectionHeader.tsx").write_text('''
type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  meta?: string;
};

export function SectionHeader({ eyebrow, title, meta }: SectionHeaderProps) {
  return (
    <header className="eiq-ds-section-header">
      <div>
        {eyebrow ? <span>{eyebrow}</span> : null}
        <h2>{title}</h2>
      </div>
      {meta ? <strong>{meta}</strong> : null}
    </header>
  );
}
'''.lstrip(), encoding="utf-8")

(components / "WorkspaceHeader.tsx").write_text('''
type WorkspaceHeaderProps = {
  eyebrow: string;
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
};

export function WorkspaceHeader({ eyebrow, title, subtitle, children }: WorkspaceHeaderProps) {
  return (
    <header className="eiq-ds-workspace-header">
      <div>
        <span>{eyebrow}</span>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {children ? <div className="eiq-ds-workspace-header__aside">{children}</div> : null}
    </header>
  );
}
'''.lstrip(), encoding="utf-8")

(components / "BriefSection.tsx").write_text('''
type BriefSectionProps = {
  label: string;
  title?: string;
  body: string;
  action?: string;
};

export function BriefSection({ label, title, body, action }: BriefSectionProps) {
  return (
    <section className="eiq-ds-brief">
      <span>{label}</span>
      {title ? <h2>{title}</h2> : null}
      <p>{body}</p>
      {action ? <b>{action}</b> : null}
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

(components / "ReportSection.tsx").write_text('''
type ReportSectionProps = {
  label: string;
  title: string;
  body: string;
  footer?: React.ReactNode;
};

export function ReportSection({ label, title, body, footer }: ReportSectionProps) {
  return (
    <section className="eiq-ds-report">
      <span>{label}</span>
      <h3>{title}</h3>
      <p>{body}</p>
      {footer ? <div className="eiq-ds-report__footer">{footer}</div> : null}
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

(components / "TimelineSection.tsx").write_text('''
type TimelineItem = {
  id: string;
  time: string;
  title: string;
  summary: string;
};

type TimelineSectionProps = {
  title: string;
  items: TimelineItem[];
};

export function TimelineSection({ title, items }: TimelineSectionProps) {
  return (
    <section className="eiq-ds-timeline">
      <h2>{title}</h2>
      {items.map((item) => (
        <article key={item.id}>
          <span>{item.time}</span>
          <strong>{item.title}</strong>
          <p>{item.summary}</p>
        </article>
      ))}
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

(components / "Metric.tsx").write_text('''
type MetricProps = {
  label: string;
  value: string | number;
};

export function Metric({ label, value }: MetricProps) {
  return (
    <div className="eiq-ds-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
'''.lstrip(), encoding="utf-8")

(base / "edgeiqDesignSystem.css").write_text(r'''
:root {
  --eiq-ds-surface: #080806;
  --eiq-ds-surface-raised: rgba(255,255,255,0.035);
  --eiq-ds-surface-hover: rgba(255,255,255,0.065);
  --eiq-ds-text-primary: #f6f3ea;
  --eiq-ds-text-secondary: rgba(246,243,234,0.72);
  --eiq-ds-text-muted: rgba(246,243,234,0.48);
  --eiq-ds-divider: rgba(246,243,234,0.10);
  --eiq-ds-success: #7edc9b;
  --eiq-ds-warning: #e6bf69;
  --eiq-ds-critical: #ef6b6b;
  --eiq-ds-radius-sm: 10px;
  --eiq-ds-radius-md: 16px;
  --eiq-ds-radius-lg: 24px;
  --eiq-ds-ease: cubic-bezier(0.2, 0.8, 0.2, 1);
}

.eiq-ds-workspace-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  padding-bottom: 26px;
  border-bottom: 1px solid var(--eiq-ds-divider);
}

.eiq-ds-workspace-header span,
.eiq-ds-section-header span,
.eiq-ds-brief span,
.eiq-ds-report span,
.eiq-ds-metric span {
  display: block;
  color: var(--eiq-ds-text-muted);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.eiq-ds-workspace-header h1 {
  margin: 8px 0 2px;
  color: var(--eiq-ds-text-primary);
  font-size: clamp(42px, 5vw, 72px);
  line-height: 0.92;
  letter-spacing: -0.07em;
}

.eiq-ds-workspace-header p {
  margin: 0;
  color: var(--eiq-ds-text-secondary);
  font-size: 15px;
  font-weight: 700;
}

.eiq-ds-section-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.eiq-ds-section-header h2 {
  margin: 5px 0 0;
  color: var(--eiq-ds-text-primary);
  font-size: 22px;
  letter-spacing: -0.04em;
}

.eiq-ds-section-header strong {
  color: var(--eiq-ds-text-muted);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.eiq-ds-brief,
.eiq-ds-report {
  padding: 28px 0;
  border-bottom: 1px solid var(--eiq-ds-divider);
}

.eiq-ds-brief h2,
.eiq-ds-report h3 {
  margin: 12px 0 0;
  color: var(--eiq-ds-text-primary);
  font-size: 28px;
  line-height: 1.08;
  letter-spacing: -0.045em;
}

.eiq-ds-brief p {
  max-width: 860px;
  margin: 14px 0 0;
  color: var(--eiq-ds-text-secondary);
  font-size: 21px;
  line-height: 1.48;
  letter-spacing: -0.03em;
}

.eiq-ds-report p {
  margin: 14px 0 0;
  color: var(--eiq-ds-text-secondary);
  font-size: 15px;
  line-height: 1.65;
}

.eiq-ds-brief b {
  display: block;
  max-width: 780px;
  margin-top: 18px;
  color: var(--eiq-ds-text-primary);
  font-size: 15px;
  line-height: 1.55;
}

.eiq-ds-status {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 9px;
  border: 1px solid var(--eiq-ds-divider);
  color: var(--eiq-ds-text-secondary);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eiq-ds-status--ready {
  color: var(--eiq-ds-success);
}

.eiq-ds-status--partial,
.eiq-ds-status--placeholder {
  color: var(--eiq-ds-warning);
}

.eiq-ds-status--error {
  color: var(--eiq-ds-critical);
}

.eiq-ds-timeline {
  padding: 28px 0;
}

.eiq-ds-timeline h2 {
  margin: 0 0 18px;
  color: var(--eiq-ds-text-primary);
  font-size: 22px;
}

.eiq-ds-timeline article {
  padding: 14px 0;
  border-top: 1px solid var(--eiq-ds-divider);
}

.eiq-ds-timeline article span {
  color: var(--eiq-ds-text-muted);
  font-size: 11px;
  font-weight: 800;
}

.eiq-ds-timeline article strong {
  display: block;
  margin-top: 6px;
  color: var(--eiq-ds-text-primary);
}

.eiq-ds-timeline article p {
  margin: 6px 0 0;
  color: var(--eiq-ds-text-secondary);
  font-size: 13px;
  line-height: 1.55;
}

.eiq-ds-metric {
  padding-top: 12px;
  border-top: 1px solid var(--eiq-ds-divider);
}

.eiq-ds-metric strong {
  display: block;
  margin-top: 4px;
  color: var(--eiq-ds-text-primary);
  font-size: 14px;
}
'''.lstrip(), encoding="utf-8")

(base / "index.ts").write_text('''
export * from "./components/WorkspaceHeader";
export * from "./components/SectionHeader";
export * from "./components/BriefSection";
export * from "./components/ReportSection";
export * from "./components/TimelineSection";
export * from "./components/StatusBadge";
export * from "./components/Metric";

export * from "./formatters/statusFormatter";
export * from "./formatters/confidenceFormatter";
export * from "./formatters/decisionFormatter";
export * from "./formatters/priorityFormatter";
export * from "./formatters/narrativeFormatter";

export * from "./tokens/typography";
export * from "./tokens/spacing";
export * from "./tokens/colours";
export * from "./tokens/motion";
export * from "./tokens/radius";
'''.lstrip(), encoding="utf-8")

main = Path("src/main.tsx")
text = main.read_text(encoding="utf-8")
import_line = 'import "./edgeiq-os/design-system/edgeiqDesignSystem.css";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, import_line)
    main.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("[EDGEIQ] Design System V2 foundation built")
