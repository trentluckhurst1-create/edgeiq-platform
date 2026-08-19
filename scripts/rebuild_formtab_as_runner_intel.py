from pathlib import Path
import re

path = Path(r".\src\components\FormTab.tsx")
text = path.read_text(encoding="utf-8")

start = text.find('  return (')
end = text.rfind('  );\n}')

if start == -1 or end == -1:
    raise SystemExit("FAILED TO FIND FormTab RETURN BLOCK")

new_return = r'''  return (
    <section className="edgeiq-runner-intel terminal-card">
      <div className="runner-intel-head">
        <img src={getSilksUrl(selected?.horse, selected?.silkUrl)} alt="" onError={silkFallback} />
        <div>
          <div className="kicker">Selected Runner Intelligence</div>
          <h2>{selected?.horse ?? "-"}</h2>
          <p>No {selected?.horseNo ?? "-"} | Bar {selected?.barrier ?? "-"} | {selected?.jockey || "-"} | {selected?.trainer || "-"}</p>
        </div>
      </div>

      <div className="runner-intel-price-grid">
        <div><span>LIVE</span><strong>{price(selected?.marketPrice)}</strong></div>
        <div><span>FAIR</span><strong>{price(selected?.ratedPrice)}</strong></div>
        <div><span>EDGE</span><strong>{selected?.edgePct != null ? `${selected.edgePct.toFixed(1)}%` : "-"}</strong></div>
        <div><span>CONF</span><strong>{selected?.modelConfidenceScore != null ? selected.modelConfidenceScore.toFixed(0) : "-"}</strong></div>
      </div>

      <div className="runner-intel-section">
        <div className="section-title">Profile</div>
        <div className="runner-intel-grid">
          <div><span>Run style</span><strong>{selected?.run_style_cluster || selected?.sectional_profile || "-"}</strong></div>
          <div><span>Tempo fit</span><strong>{selected?.tempo_fit || "-"}</strong></div>
          <div><span>Late power</span><strong>{selected?.late_power_index != null ? selected.late_power_index.toFixed(0) : "-"}</strong></div>
          <div><span>Burst</span><strong>{selected?.burst_index != null ? selected.burst_index.toFixed(0) : "-"}</strong></div>
          <div><span>Fatigue</span><strong>{selected?.fatigue_risk_index != null ? selected.fatigue_risk_index.toFixed(0) : "-"}</strong></div>
          <div><span>Sectional</span><strong>{selected?.sectional_weapon_score != null ? selected.sectional_weapon_score.toFixed(0) : "-"}</strong></div>
        </div>
      </div>

      <div className="runner-intel-section">
        <div className="section-title">Record</div>
        <div className="runner-intel-records">
          <div><span>Career</span><strong>{record(selectedCareerStats?.careerStarts, selectedCareerStats?.careerWins, selectedCareerStats?.careerSeconds, selectedCareerStats?.careerThirds)}</strong></div>
          <div><span>Track</span><strong>{record(selectedCareerStats?.trackStarts, selectedCareerStats?.trackWins, selectedCareerStats?.trackSeconds, selectedCareerStats?.trackThirds)}</strong></div>
          <div><span>Distance</span><strong>{record(selectedCareerStats?.distanceStarts, selectedCareerStats?.distanceWins, selectedCareerStats?.distanceSeconds, selectedCareerStats?.distanceThirds)}</strong></div>
          <div><span>Track/Dist</span><strong>{record(selectedCareerStats?.trackDistanceStarts, selectedCareerStats?.trackDistanceWins, selectedCareerStats?.trackDistanceSeconds, selectedCareerStats?.trackDistanceThirds)}</strong></div>
        </div>
      </div>

      <div className="runner-intel-section">
        <div className="section-title">Last 5 official starts</div>
        <div className="runner-intel-runs">
          {official.map((run) => (
            <div key={run.id}>
              <span>{dateShort(run.runDate)}</span>
              <strong>{safe(run.track)}</strong>
              <span>{run.distance ? `${run.distance}m` : "-"}</span>
              <span>{safe(run.finishPos)}</span>
              <em>{displayRating(run)}</em>
            </div>
          ))}
          {!official.length ? <div className="empty">Insufficient history.</div> : null}
        </div>
      </div>
    </section>
  );
'''

text = text[:start] + new_return + text[end+5:]

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("RIGHT PANEL REBUILT AS SELECTED RUNNER INTELLIGENCE")
print("=" * 80)
