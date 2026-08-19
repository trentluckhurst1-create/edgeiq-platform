type Row = Record<string, any>;

type RaceWeatherWorkspaceProps = {
  header: Row;
  railDisplay: string;
  displayExpectedTempo: string;
  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  track: (row: Row) => string;
  distance: (row: Row) => string;
  trackCondition: (row: Row) => string;
  raceClass: (row: Row) => string;
};

export function RaceWeatherWorkspace(props: RaceWeatherWorkspaceProps) {
  const { header, railDisplay, displayExpectedTempo, firstText, track, distance, trackCondition, raceClass } = props;

  const conditionValue = (keys: string[], fallback = "Pending") => {
    const raw = firstText(header, keys, "");
    return raw && raw !== "-" ? raw : fallback;
  };

  const trackPattern = conditionValue(["track_pattern", "bias_pattern", "current_track_pattern"], "Neutral");
  const leaderBias = conditionValue(["leader_bias", "front_runner_bias"], "Neutral");
  const insideBias = conditionValue(["inside_bias", "inside_lane_bias"], "Neutral");
  const outsideBias = conditionValue(["outside_bias", "outside_lane_bias"], "Neutral");
  const wind = [conditionValue(["wind_direction", "wind_dir"], ""), conditionValue(["wind_speed", "wind"], "")]
    .filter((value) => value && value !== "Pending")
    .join(" ") || "Pending";

  const conditionCards = [
    { label: "Track", value: trackCondition(header), icon: "track" },
    { label: "Rail", value: railDisplay, icon: "rail" },
    { label: "Wind", value: wind, icon: "wind" },
    { label: "Rainfall", value: conditionValue(["rainfall", "rainfall_24h", "rain_24h"]), icon: "rain" },
    { label: "Irrigation", value: conditionValue(["irrigation", "irrigation_24h"]), icon: "water" },
    { label: "Temperature", value: conditionValue(["temperature", "temp"]), icon: "temp" },
    { label: "Humidity", value: conditionValue(["humidity"]), icon: "humidity" },
    { label: "Penetrometer", value: conditionValue(["penetrometer", "penetrometer_reading"]), icon: "pen" },
  ];

  return (
    <section className="edgeiq-weather-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-conditions-v1-lock edgeiq-conditions-final-lock">
      <div className="edgeiq-tab-heading edgeiq-product-v4-section-title">
        <span>CONDITIONS</span>
        <strong>Conditions Intelligence</strong>
        <em>Track, weather, bias and race impact.</em>
      </div>

      <div className="edgeiq-conditions-v1-cards edgeiq-conditions-final-cards">
        {conditionCards.map((card) => (
          <article key={`conditions-v1-${card.label}`}>
            <i className={`edgeiq-conditions-card-icon is-${card.icon}`} aria-hidden="true" />
            <span>{card.label}</span>
            <strong>{card.value && card.value !== "-" ? card.value : "Pending"}</strong>
          </article>
        ))}
      </div>

      <div className="edgeiq-conditions-final-grid">
        <section>
          <strong>Track Pattern Intelligence</strong>
          {[
            ["Current Track Pattern", trackPattern],
            ["Leader Bias", leaderBias],
            ["Inside Bias", insideBias],
            ["Outside Bias", outsideBias],
            ["Track Evolution", conditionValue(["track_evolution", "track_trend"], "Pending")],
          ].map(([label, value]) => <div key={`conditions-pattern-${label}`}><span>{label}</span><em>{value}</em></div>)}
        </section>

        <section>
          <strong>Historical Profile</strong>
          {[
            ["Track", track(header)],
            ["Distance", distance(header)],
            ["Condition", trackCondition(header)],
            ["Rail", railDisplay],
            ["Race Grade", raceClass(header)],
          ].map(([label, value]) => <div key={`conditions-history-${label}`}><span>{label}</span><em>{value}</em></div>)}
        </section>

        <section>
          <strong>Weather Impact</strong>
          {[
            ["Wind", wind],
            ["Rainfall", conditionCards[3].value],
            ["Temperature", conditionCards[5].value],
            ["Humidity", conditionCards[6].value],
            ["Surface Change", conditionValue(["surface_change", "track_condition_change"], "Pending")],
          ].map(([label, value]) => <div key={`conditions-weather-${label}`}><span>{label}</span><em>{value}</em></div>)}
        </section>

        <section>
          <strong>Expected Race Shape</strong>
          {[
            ["Tempo Impact", displayExpectedTempo !== "-" ? displayExpectedTempo : "Pending"],
            ["Lane Impact", insideBias !== "Neutral" ? `Inside: ${insideBias}` : outsideBias !== "Neutral" ? `Outside: ${outsideBias}` : "Neutral"],
            ["Likely Suited", conditionValue(["conditions_suited", "track_suited"], "Pending")],
            ["Likely Disadvantaged", conditionValue(["conditions_disadvantaged", "track_disadvantaged"], "Pending")],
          ].map(([label, value]) => <div key={`conditions-shape-${label}`}><span>{label}</span><em>{value}</em></div>)}
        </section>

        <section className="edgeiq-conditions-final-summary">
          <strong>EDGEiQ Conditions Summary</strong>
          <p>{conditionValue(["conditions_summary", "track_weather_summary"], `Current profile: ${trackCondition(header)} with rail ${railDisplay}. Bias intelligence is ${trackPattern.toLowerCase()}.`)}</p>
        </section>
      </div>
    </section>
  );
}
