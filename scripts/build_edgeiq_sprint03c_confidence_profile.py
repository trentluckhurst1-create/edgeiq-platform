from pathlib import Path

services = Path("src/edgeiq-os/services")
components = Path("src/edgeiq-os/command/components")
command = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

services.mkdir(parents=True, exist_ok=True)
components.mkdir(parents=True, exist_ok=True)

(services / "confidence-profile.ts").write_text(r'''
import { buildAgreementMatrix } from "./agreement-matrix";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

export type ConfidenceSignal = {
  label: string;
  status: string;
  strength: number;
  direction: "SUPPORTING" | "WATCH" | "NEUTRAL";
};

export type ConfidenceProfile = {
  label: string;
  band: "LOW" | "DEVELOPING" | "MODERATE" | "HIGH" | "VERY HIGH";
  agreement: number;
  strongestSignal: ConfidenceSignal;
  weakestSignal: ConfidenceSignal;
  signals: ConfidenceSignal[];
  summary: string;
};

function bandFromAgreement(agreement: number): ConfidenceProfile["band"] {
  if (agreement >= 90) return "VERY HIGH";
  if (agreement >= 75) return "HIGH";
  if (agreement >= 55) return "MODERATE";
  if (agreement >= 35) return "DEVELOPING";
  return "LOW";
}

function strengthFromStatus(status: string): number {
  const value = status.toLowerCase();

  if (
    value.includes("elite") ||
    value.includes("very high") ||
    value.includes("high") ||
    value.includes("strong") ||
    value.includes("confirm") ||
    value.includes("mapped") ||
    value.includes("assessed") ||
    value.includes("active")
  ) {
    return 90;
  }

  if (
    value.includes("positive") ||
    value.includes("moderate") ||
    value.includes("normal") ||
    value.includes("on_pace") ||
    value.includes("forward")
  ) {
    return 72;
  }

  if (
    value.includes("watch") ||
    value.includes("building") ||
    value.includes("developing") ||
    value.includes("unknown")
  ) {
    return 48;
  }

  return 60;
}

function directionFromStrength(strength: number): ConfidenceSignal["direction"] {
  if (strength >= 70) return "SUPPORTING";
  if (strength >= 50) return "NEUTRAL";
  return "WATCH";
}

export function buildConfidenceProfile(): ConfidenceProfile {
  const agreement = buildAgreementMatrix();
  const pressure = buildPressureEngine();
  const tempo = buildTempoEngine();
  const position = buildPositionEngine();
  const speed = buildSpeedProfile();
  const track = buildTrackSignature();

  const rawSignals = [
    { label: "Pressure Engine", status: pressure.band },
    { label: "Tempo Engine", status: tempo.band },
    { label: "Position Engine", status: position.position },
    { label: "SpeedProfile", status: speed.confidence },
    { label: "TrackSignature", status: track.todayPattern },
    { label: "Agreement Matrix", status: `${agreement.agreement}%` },
  ];

  const signals = rawSignals.map((signal) => {
    const strength =
      signal.label === "Agreement Matrix"
        ? agreement.agreement
        : strengthFromStatus(signal.status);

    return {
      ...signal,
      strength,
      direction: directionFromStrength(strength),
    };
  });

  const sorted = [...signals].sort((a, b) => b.strength - a.strength);
  const strongestSignal = sorted[0] ?? signals[0];
  const weakestSignal = sorted[sorted.length - 1] ?? signals[0];

  const band = bandFromAgreement(agreement.agreement);

  return {
    label: "Operational Confidence",
    band,
    agreement: agreement.agreement,
    strongestSignal,
    weakestSignal,
    signals,
    summary:
      `${band.replace("_", " ")} confidence is currently driven by ${strongestSignal.label}. ` +
      `${weakestSignal.label} remains the weakest signal and should stay under observation.`,
  };
}
''', encoding="utf-8")

(components / "ConfidenceProfile.tsx").write_text(r'''
import { buildConfidenceProfile } from "../../services/confidence-profile";

function pct(value: number): string {
  return `${Math.max(0, Math.min(100, value))}%`;
}

export function ConfidenceProfile() {
  const profile = buildConfidenceProfile();

  return (
    <section className="eiq-confidence-profile">
      <header>
        <span>EDGEiQ Intelligence</span>
        <strong>{profile.label}</strong>
        <b>{profile.band.replace("_", " ")}</b>
      </header>

      <p>{profile.summary}</p>

      <div className="eiq-confidence-profile__meta">
        <article>
          <span>Overall Agreement</span>
          <strong>{profile.agreement}%</strong>
        </article>

        <article>
          <span>Strongest Signal</span>
          <strong>{profile.strongestSignal.label}</strong>
          <small>{profile.strongestSignal.status}</small>
        </article>

        <article>
          <span>Weakest Signal</span>
          <strong>{profile.weakestSignal.label}</strong>
          <small>{profile.weakestSignal.status}</small>
        </article>
      </div>

      <div className="eiq-confidence-profile__signals">
        {profile.signals.map((signal) => (
          <article key={signal.label}>
            <div>
              <strong>{signal.label}</strong>
              <span>{signal.direction}</span>
            </div>

            <div className="eiq-confidence-profile__bar">
              <i style={{ width: pct(signal.strength) }} />
            </div>

            <small>{signal.status}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
''', encoding="utf-8")

text = command.read_text(encoding="utf-8")

if "ConfidenceProfile" not in text:
    text = text.replace(
        'import { DecisionTimeline } from "./components/DecisionTimeline";',
        'import { DecisionTimeline } from "./components/DecisionTimeline";\nimport { ConfidenceProfile } from "./components/ConfidenceProfile";'
    )

    text = text.replace(
        '          <AssessmentJourney journey={assessmentJourney} />',
        '          <AssessmentJourney journey={assessmentJourney} />\n\n          <ConfidenceProfile />'
    )

command.write_text(text, encoding="utf-8")

with css.open("a", encoding="utf-8") as f:
    f.write(r'''

/* ==========================================================================
   EDGEiQ Sprint 03C — Operational Confidence Profile
   ========================================================================== */

.eiq-confidence-profile {
  margin-top: 34px;
  padding: 34px;
  border: 1px solid rgba(246, 243, 234, 0.085);
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(126, 220, 155, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.014));
}

.eiq-confidence-profile header {
  display: grid;
  gap: 8px;
}

.eiq-confidence-profile header span,
.eiq-confidence-profile__meta span,
.eiq-confidence-profile__signals span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-confidence-profile header strong {
  color: #f6f3ea;
  font-size: clamp(30px, 3vw, 44px);
  line-height: 0.98;
  letter-spacing: -0.06em;
}

.eiq-confidence-profile header b {
  color: #7edc9b;
  font-size: 18px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-confidence-profile > p {
  max-width: 880px;
  margin: 22px 0 0;
  color: rgba(246, 243, 234, 0.72);
  font-size: 15px;
  line-height: 1.65;
}

.eiq-confidence-profile__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
  margin-top: 30px;
}

.eiq-confidence-profile__meta article {
  padding-top: 15px;
  border-top: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-confidence-profile__meta strong {
  display: block;
  margin-top: 9px;
  color: #f6f3ea;
  font-size: 24px;
  line-height: 1;
  letter-spacing: -0.05em;
}

.eiq-confidence-profile__meta small {
  display: block;
  margin-top: 8px;
  color: rgba(246, 243, 234, 0.50);
  font-size: 12px;
}

.eiq-confidence-profile__signals {
  display: grid;
  gap: 16px;
  margin-top: 32px;
}

.eiq-confidence-profile__signals article {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 110px;
  gap: 16px;
  align-items: center;
  padding-top: 14px;
  border-top: 1px solid rgba(246, 243, 234, 0.075);
}

.eiq-confidence-profile__signals strong {
  display: block;
  color: #f6f3ea;
  font-size: 13px;
}

.eiq-confidence-profile__signals small {
  color: rgba(246, 243, 234, 0.56);
  font-size: 12px;
  text-align: right;
}

.eiq-confidence-profile__bar {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(246, 243, 234, 0.09);
}

.eiq-confidence-profile__bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(126, 220, 155, 0.56), rgba(126, 220, 155, 0.95));
}

@media (max-width: 900px) {
  .eiq-confidence-profile__meta,
  .eiq-confidence-profile__signals article {
    grid-template-columns: 1fr;
  }

  .eiq-confidence-profile__signals small {
    text-align: left;
  }
}
''')

print("[EDGEIQ] Sprint03C Operational Confidence Profile built")
