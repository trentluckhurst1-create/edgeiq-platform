from pathlib import Path

tsx = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = tsx.read_text(encoding="utf-8")

old = '''      <section className={`discipline-health-banner ${health.state.toLowerCase()}`}>
        <strong>{health.state}</strong>
        <span>{health.warnings.length ? health.warnings.join(" | ") : "All production discipline feeds are online."}</span>
      </section>

      <section className="race-info-panel" aria-label="Race execution state">
        {metrics.map((item) => <Metric key={`${item.label}-${item.value}`} item={item} />)}
      </section>
'''

new = '''      <section className="race-briefing-banner" aria-label="Race briefing">
        <div className="race-briefing-main">
          <span>Race Briefing</span>
          <strong>{[clean(currentRace?.track), currentRace?.raceNo ? `R${currentRace.raceNo}` : ""].filter(has).join(" ") || "Selected Race"}</strong>
          <em>{[currentRace?.distance ? `${currentRace.distance}m` : "", clean(currentRace?.raceClass), clean(currentRace?.todayTrackCondition)].filter(has).join(" | ")}</em>
        </div>

        <div className="race-briefing-grid">
          <div>
            <span>Runners</span>
            <strong>{activeField.length}/{field.length}</strong>
          </div>
          <div>
            <span>Clock</span>
            <strong>{clockText}</strong>
          </div>
          <div>
            <span>Shape</span>
            <strong>{projectedShape || "-"}</strong>
          </div>
          <div>
            <span>Pressure</span>
            <strong>{pressure || "-"}</strong>
          </div>
        </div>
      </section>
'''

if old not in text:
    raise SystemExit("Could not find operational strip block. No changes made.")

text = text.replace(old, new)
tsx.write_text(text, encoding="utf-8")
print("RACE BRIEFING BANNER INSERTED")

css = Path(r".\src\components\race-intelligence-screen.css")
css_text = css.read_text(encoding="utf-8")

css_text += r'''

/* =============================================================================
EDGEIQ INTELLIGENCE V4 RACE BRIEFING
============================================================================= */

.race-briefing-banner {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(0, 2.1fr);
  gap: 6px;
  align-items: stretch;
  border: 1px solid rgba(45, 212, 191, 0.16);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(5, 16, 24, 0.96), rgba(2, 8, 14, 0.98));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.026);
  padding: 6px;
}

.race-briefing-main,
.race-briefing-grid > div {
  border: 1px solid rgba(148, 163, 184, 0.10);
  border-radius: 7px;
  background: rgba(2, 8, 16, 0.62);
  min-width: 0;
}

.race-briefing-main {
  padding: 8px 10px;
}

.race-briefing-main span,
.race-briefing-grid span {
  display: block;
  color: #718398;
  font-size: 7px;
  font-weight: 950;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.race-briefing-main strong {
  display: block;
  margin-top: 3px;
  color: #f8fafc;
  font-size: 15px;
  font-weight: 950;
  letter-spacing: .02em;
}

.race-briefing-main em {
  display: block;
  margin-top: 3px;
  color: #9fb0c4;
  font-size: 9px;
  font-style: normal;
  font-weight: 850;
}

.race-briefing-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.race-briefing-grid > div {
  padding: 8px 10px;
}

.race-briefing-grid strong {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: #f8fafc;
  font-size: 12px;
  font-weight: 950;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .race-briefing-banner {
    grid-template-columns: 1fr;
  }

  .race-briefing-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
'''
css.write_text(css_text, encoding="utf-8")
print("RACE BRIEFING CSS ADDED")
