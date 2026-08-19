from pathlib import Path

components = Path("src/edgeiq-os/command/components")

(components / "OperationalAlertsBar.tsx").write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";

type OperationalAlertsBarProps = {
  raceState: OperationalRaceState;
};

export function OperationalAlertsBar({ raceState }: OperationalAlertsBarProps) {
  const partial = raceState.feedHealth.filter((feed) => feed.status !== "READY");
  const criticalEvents = raceState.events.filter((event) => event.severity === "CRITICAL" || event.severity === "WARNING");

  const alerts = [
    `${raceState.decision.state} mode`,
    `${raceState.confidence}% confidence`,
    partial.length ? `${partial.length} engine(s) pending` : "All engines available",
    criticalEvents.length ? `${criticalEvents.length} watch item(s)` : "No critical alerts",
  ];

  return (
    <section className="eiq-operational-alerts">
      {alerts.map((alert) => (
        <span key={alert}>● {alert}</span>
      ))}
    </section>
  );
}
''', encoding="utf-8")

(components / "OperationalInbox.tsx").write_text(r'''
import type { OperationalEvent } from "../../services/operational-state";

type OperationalInboxProps = {
  events: OperationalEvent[];
};

export function OperationalInbox({ events }: OperationalInboxProps) {
  return (
    <section className="eiq-operational-inbox">
      <header>
        <span>Live Events</span>
        <strong>{events.length}</strong>
      </header>

      <div>
        {events.slice(0, 8).map((event) => (
          <article key={event.id}>
            <time>{event.time}</time>
            <div>
              <strong>{event.title}</strong>
              <p>{event.detail}</p>
              <small>{event.source} · {event.severity}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
''', encoding="utf-8")

(components / "EngineAgreementMatrix.tsx").write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";

type EngineAgreementMatrixProps = {
  raceState: OperationalRaceState;
};

export function EngineAgreementMatrix({ raceState }: EngineAgreementMatrixProps) {
  return (
    <section className="eiq-engine-matrix">
      <header>
        <span>Engine Agreement</span>
        <strong>{raceState.correlation.agreementBand}</strong>
      </header>

      <div className="eiq-engine-matrix__grid">
        {raceState.feedHealth.map((feed) => {
          const coverage = raceState.coverage.find((item) => item.key === feed.key);
          const ready = feed.status === "READY";

          return (
            <article key={feed.key} className={ready ? "is-ready" : "is-partial"}>
              <span>{ready ? "✓" : "△"}</span>
              <strong>{feed.label}</strong>
              <small>{ready ? "Aligned" : "Pending"}</small>
              <em>{coverage?.coveragePct ?? 0}%</em>
            </article>
          );
        })}
      </div>
    </section>
  );
}
''', encoding="utf-8")

(components / "ConfidenceTimeline.tsx").write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";

type ConfidenceTimelineProps = {
  raceState: OperationalRaceState;
};

export function ConfidenceTimeline({ raceState }: ConfidenceTimelineProps) {
  const base = Math.max(20, raceState.confidence - 8);
  const points = [
    { label: "Open", value: base },
    { label: "Shape", value: Math.min(95, base + 3) },
    { label: "Explain", value: Math.min(95, base + 7) },
    { label: "Current", value: raceState.confidence },
  ];

  return (
    <section className="eiq-confidence-timeline">
      <header>
        <span>Confidence Trend</span>
        <strong>{raceState.confidence}%</strong>
      </header>

      <div className="eiq-confidence-timeline__track">
        {points.map((point) => (
          <article key={point.label}>
            <b style={{ height: `${point.value}%` }} />
            <span>{point.label}</span>
            <small>{point.value}%</small>
          </article>
        ))}
      </div>

      <p>{raceState.confidence >= base ? "Confidence stable to improving." : "Confidence under pressure."}</p>
    </section>
  );
}
''', encoding="utf-8")

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = workspace.read_text(encoding="utf-8")

imports = [
  'import { OperationalAlertsBar } from "./components/OperationalAlertsBar";',
  'import { OperationalInbox } from "./components/OperationalInbox";',
  'import { EngineAgreementMatrix } from "./components/EngineAgreementMatrix";',
  'import { ConfidenceTimeline } from "./components/ConfidenceTimeline";',
]

for imp in imports:
    if imp not in text:
        text = text.replace(
            'import { OperationalTimelinePanel } from "./components/OperationalTimelinePanel";',
            f'import {{ OperationalTimelinePanel }} from "./components/OperationalTimelinePanel";\n{imp}'
        )

if "<OperationalAlertsBar" not in text:
    text = text.replace(
'''          <LiveStatusStrip items={liveStatus} />
        </header>''',
'''          <LiveStatusStrip items={liveStatus} />
        </header>

        <OperationalAlertsBar raceState={raceState} />'''
    )

if "<EngineAgreementMatrix" not in text:
    text = text.replace(
'''            <section className="eiq-command-findings">''',
'''            <section className="eiq-command-ops-grid">
              <EngineAgreementMatrix raceState={raceState} />
              <ConfidenceTimeline raceState={raceState} />
              <OperationalInbox events={raceState.events} />
            </section>

            <section className="eiq-command-findings">'''
    )

text = text.replace(
    '<OperationalTimelinePanel events={raceState.events} />',
    ''
)

workspace.write_text(text, encoding="utf-8")

css = Path("src/styles/edgeiqProductTerminalV1.css")
css_text = css.read_text(encoding="utf-8", errors="ignore")

addition = r'''

/* EDGEIQ OS V2 Live Operations Layer */
.eiq-operational-alerts {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 0 0 16px;
}

.eiq-operational-alerts span {
  border: 1px solid rgba(244,195,106,0.22);
  background: rgba(244,195,106,0.07);
  color: #f4c36a;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-command-ops-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr 1.2fr;
  gap: 14px;
}

.eiq-engine-matrix,
.eiq-confidence-timeline,
.eiq-operational-inbox {
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(8, 12, 18, 0.78);
  border-radius: 18px;
  padding: 16px;
  min-height: 240px;
}

.eiq-engine-matrix header,
.eiq-confidence-timeline header,
.eiq-operational-inbox header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.eiq-engine-matrix header span,
.eiq-confidence-timeline header span,
.eiq-operational-inbox header span {
  color: rgba(255,255,255,0.52);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-engine-matrix header strong,
.eiq-confidence-timeline header strong,
.eiq-operational-inbox header strong {
  color: #fff;
}

.eiq-engine-matrix__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.eiq-engine-matrix__grid article {
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  border-radius: 12px;
  padding: 10px;
  display: grid;
  gap: 3px;
}

.eiq-engine-matrix__grid article span {
  color: #6ee7b7;
  font-weight: 900;
}

.eiq-engine-matrix__grid article.is-partial span {
  color: #f4c36a;
}

.eiq-engine-matrix__grid article strong {
  color: #fff;
  font-size: 12px;
}

.eiq-engine-matrix__grid article small,
.eiq-engine-matrix__grid article em {
  color: rgba(255,255,255,0.5);
  font-size: 11px;
  font-style: normal;
}

.eiq-confidence-timeline__track {
  height: 150px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  align-items: end;
  margin: 16px 0 10px;
}

.eiq-confidence-timeline__track article {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: end;
  align-items: center;
  gap: 6px;
}

.eiq-confidence-timeline__track b {
  display: block;
  width: 100%;
  border-radius: 10px 10px 4px 4px;
  background: linear-gradient(180deg, rgba(110,231,183,0.9), rgba(86,132,255,0.45));
  min-height: 20px;
}

.eiq-confidence-timeline__track span,
.eiq-confidence-timeline__track small {
  color: rgba(255,255,255,0.56);
  font-size: 11px;
}

.eiq-confidence-timeline p {
  color: rgba(255,255,255,0.62);
  margin: 0;
}

.eiq-operational-inbox > div {
  display: grid;
  gap: 10px;
  max-height: 190px;
  overflow: auto;
}

.eiq-operational-inbox article {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 10px;
  border-top: 1px solid rgba(255,255,255,0.07);
  padding-top: 10px;
}

.eiq-operational-inbox time {
  color: #f4c36a;
  font-size: 12px;
  font-weight: 800;
}

.eiq-operational-inbox strong {
  display: block;
  color: #fff;
  font-size: 12px;
}

.eiq-operational-inbox p {
  margin: 3px 0;
  color: rgba(255,255,255,0.62);
  font-size: 12px;
  line-height: 1.4;
}

.eiq-operational-inbox small {
  color: rgba(255,255,255,0.42);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
'''

if "EDGEIQ OS V2 Live Operations Layer" not in css_text:
    css_text += addition

css.write_text(css_text, encoding="utf-8")

print("[EDGEIQ] Live operations layer built and mounted")
