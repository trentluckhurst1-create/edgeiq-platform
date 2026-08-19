from pathlib import Path

home = Path("src/edgeiq-os/home/EdgeiqOsHome.tsx")
shell = Path("src/edgeiq-os/shell/EdgeiqOsShell.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

home.write_text(r'''
import { WorkspaceHeader, BriefSection, SectionHeader } from "../design-system";

const todayStats = [
  { label: "Meetings", value: "Victoria", note: "Active racing universe" },
  { label: "Races", value: "Pending Feed", note: "Race universe connecting" },
  { label: "Highest Confidence", value: "Pending", note: "Requires race selection" },
  { label: "Largest Overlay", value: "Pending", note: "Market validation pending" },
  { label: "Weather", value: "Stable", note: "Environment intelligence reserved" },
];

const intelligenceItems = [
  {
    title: "Open Command",
    summary: "Move into the current operational race briefing.",
    action: "COMMAND",
  },
  {
    title: "Race Situation",
    summary: "Review pressure, tempo, lanes and tactical advantage.",
    action: "RACE",
  },
  {
    title: "Runner Dossiers",
    summary: "Assess each runner through strengths, risks and today’s fit.",
    action: "RUNNERS",
  },
  {
    title: "Review",
    summary: "Compare assessment, outcome and model learning after the race.",
    action: "REVIEW",
  },
];

export function EdgeiqOsHome() {
  return (
    <section className="eiq-os3-today">
      <WorkspaceHeader
        eyebrow="EDGEiQ / Victoria"
        title="TODAY"
        subtitle="Race-day intelligence universe"
      />

      <BriefSection
        label="Today’s Briefing"
        title="Victoria racing intelligence is online."
        body="EDGEiQ is preparing the day’s operational view. The system will surface confidence, overlays, race volatility and environmental risks as the active race universe connects."
        action="Start in COMMAND for the current operational briefing, then move through RACE, RUNNERS and REVIEW as intelligence matures."
      />

      <section className="eiq-os3-today__section">
        <SectionHeader
          eyebrow="Universe"
          title="Today’s Intelligence"
          meta="Mission control"
        />

        <div className="eiq-os3-today__stats">
          {todayStats.map((item) => (
            <article key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <p>{item.note}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="eiq-os3-today__section">
        <SectionHeader
          eyebrow="Workflow"
          title="Operating Path"
          meta="Observe → Decide → Review"
        />

        <div className="eiq-os3-today__path">
          {intelligenceItems.map((item) => (
            <article key={item.title}>
              <span>{item.action}</span>
              <strong>{item.title}</strong>
              <p>{item.summary}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

if shell.exists():
    text = shell.read_text(encoding="utf-8")
    replacements = {
        "FIELD": "TODAY",
        "MAP": "RACE",
        "PERFORMANCE": "RUNNERS",
        "CONDITIONS": "REVIEW",
    }
    for old, new in replacements.items():
        text = text.replace(f'>{old}<', f'>{new}<')
        text = text.replace(f'"{old}"', f'"{new}"')
    shell.write_text(text, encoding="utf-8")

css_block = r'''

/* ==========================================================================
   EDGEiQ OS 3.0 — TODAY Mission Control
   ========================================================================== */

.eiq-os3-today {
  min-height: 100%;
  padding: 28px;
  color: var(--eiq-ds-text-primary, #f6f3ea);
}

.eiq-os3-today__section {
  padding: 30px 0;
  border-bottom: 1px solid var(--eiq-ds-divider, rgba(246, 243, 234, 0.10));
}

.eiq-os3-today__stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 22px;
}

.eiq-os3-today__stats article,
.eiq-os3-today__path article {
  padding-top: 16px;
  border-top: 1px solid rgba(246, 243, 234, 0.14);
}

.eiq-os3-today__stats span,
.eiq-os3-today__path span {
  display: block;
  color: rgba(246, 243, 234, 0.48);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-os3-today__stats strong,
.eiq-os3-today__path strong {
  display: block;
  margin-top: 10px;
  color: #f6f3ea;
  font-size: 20px;
  line-height: 1.05;
  letter-spacing: -0.045em;
}

.eiq-os3-today__stats p,
.eiq-os3-today__path p {
  margin: 10px 0 0;
  color: rgba(246, 243, 234, 0.56);
  font-size: 12px;
  line-height: 1.55;
}

.eiq-os3-today__path {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 22px;
}

@media (max-width: 1180px) {
  .eiq-os3-today__stats,
  .eiq-os3-today__path {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
'''

css.write_text(css.read_text(encoding="utf-8") + css_block, encoding="utf-8")

print("[EDGEIQ] OS 3.0 TODAY mission control built")
