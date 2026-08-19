
import { CommandService } from "../../services/CommandService";

function pct(value: number): string {
  return `${Math.max(0, Math.min(100, value))}%`;
}

export function ConfidenceProfile() {
  const profile = CommandService.buildConfidenceProfile();

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
