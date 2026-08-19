from pathlib import Path
import re

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

# Clean tipping/value language from visible copy only.
replacements = {
    "Top Win Chance": "Rating Reference",
    "TOP WIN CHANCE": "RATING REFERENCE",
    "Best Value": "Price Reference",
    "BEST VALUE": "PRICE REFERENCE",
    "Largest Overlay": "Price Gap Reference",
    "LARGEST OVERLAY": "PRICE GAP REFERENCE",
    "Largest Underlay": "Market Compression",
    "LARGEST UNDERLAY": "MARKET COMPRESSION",
    "Top Call": "Rating Reference",
    "TOP CALL": "RATING REFERENCE",
    "Main Risk": "Race Watchpoint",
    "MAIN RISK": "RACE WATCHPOINT",
    "Final Call": "Market Read",
    "FINAL CALL": "MARKET READ",
    "EDGEiQ Call": "EDGEiQ Read",
    "EDGEIQ CALL": "EDGEIQ READ",
    "Why It Leads": "Why It Rates Here",
    "WHY IT LEADS": "WHY IT RATES HERE",
    "Best Bet": "Rating Reference",
    "BEST BET": "RATING REFERENCE",
    "Overlay": "Price Gap",
    "OVERLAY": "PRICE GAP",
    "Underlay": "Market Compression",
    "UNDERLAY": "MARKET COMPRESSION",
}

for old, new in replacements.items():
    text = text.replace(old, new)

start_match = re.search(r'\n\s*\{intelMode === "COMMAND" \? \(', text)
end_match = re.search(r'\n\s*\{intelMode === "MAP" \? \(', text)

if not start_match or not end_match or end_match.start() <= start_match.start():
    raise SystemExit("COMMAND block boundaries not found. Restore checkpoint and inspect manually.")

start = start_match.start()
end = end_match.start()

new_command = r'''
      {intelMode === "COMMAND" ? (
      <section style={evidenceSectionStyle}>
        <div style={titleStyle}>
          <span>Race Intelligence Command</span>
          <em>Race structure, market state and investigation starting points</em>
        </div>

        {(() => {
          const commandRunners = activeRaceRows.filter((item) => !isScratched(item));
          const fieldSize = commandRunners.length;
          const pricedCount = commandRunners.filter((item) => (livePrice(item.row, item.bet) ?? 0) > 0).length;
          const edgeiqPriceCount = commandRunners.filter((item) => (limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet) ?? 0) > 0).length;

          const commandRatingRows = commandRunners
            .map((item) => ({ item, rating: projectionRatingValue(item) }))
            .filter((entry): entry is { item: EnrichedRunner; rating: number } => entry.rating !== null && Number.isFinite(entry.rating))
            .sort((a, b) => b.rating - a.rating);

          const commandLastStartRows = commandRunners
            .map((item) => ({ item, rating: firstNum(item.runnerForm, ["last_start_rating", "rating_1", "run_rating_final", "performance_rating"]) }))
            .filter((entry): entry is { item: EnrichedRunner; rating: number } => entry.rating !== null && Number.isFinite(entry.rating))
            .sort((a, b) => b.rating - a.rating);

          const commandPeakRows = commandRunners
            .map((item) => ({ item, rating: firstNum(item.runnerForm, ["peak_rating", "best_rating_last5", "peak", "best_rating"]) }))
            .filter((entry): entry is { item: EnrichedRunner; rating: number } => entry.rating !== null && Number.isFinite(entry.rating))
            .sort((a, b) => b.rating - a.rating);

          const commandTrajectoryRows = commandRunners
            .map((item) => ({
              item,
              score: firstNum((item as any).horseTrajectory || (item as any).trajectory || (item as any).horseProjection || (item as any).projection, ["trajectory_score", "improvement_probability", "breakout_probability"]),
            }))
            .filter((entry): entry is { item: EnrichedRunner; score: number } => entry.score !== null && Number.isFinite(entry.score))
            .sort((a, b) => b.score - a.score);

          const commandRunStyle = (item: EnrichedRunner): string =>
            firstText(item.runnerIntel, ["settling_band", "run_style", "settling_profile", "settling"], "")
              .replace(/_/g, " ")
              .toUpperCase();

          const leaderCount = commandRunners.filter((item) => {
            const style = commandRunStyle(item);
            return style.includes("LEAD") || style.includes("ON PACE") || style.includes("PACE");
          }).length;

          const backmarkerCount = commandRunners.filter((item) => commandRunStyle(item).includes("BACK")).length;

          const todayRatings = commandRatingRows.map((entry) => entry.rating);
          const ratingAvg = todayRatings.length ? todayRatings.reduce((sum, value) => sum + value, 0) / todayRatings.length : null;
          const ratingSpread =
            todayRatings.length >= 2
              ? Math.max(...todayRatings) - Math.min(...todayRatings)
              : null;

          const tempoRead =
            fieldSize === 0
              ? "FIELD LOADING"
              : leaderCount >= Math.max(4, Math.ceil(fieldSize * 0.35))
                ? "PRESSURE LIKELY"
                : leaderCount <= 1
                  ? "TACTICAL"
                  : "BALANCED";

          const raceShapeRead =
            fieldSize === 0
              ? "FIELD LOADING"
              : leaderCount > backmarkerCount
                ? "FORWARD SHAPE"
                : backmarkerCount > leaderCount
                  ? "LATE RUNNERS INVOLVED"
                  : "EVEN SHAPE";

          const pressureRead =
            leaderCount >= Math.max(4, Math.ceil(fieldSize * 0.35))
              ? "HIGH"
              : leaderCount >= 2
                ? "MODERATE"
                : "LOW";

          const lateSpeedRead =
            backmarkerCount >= Math.max(3, Math.ceil(fieldSize * 0.25))
              ? "RELEVANT"
              : "STANDARD";

          const varianceRead =
            ratingSpread === null
              ? "FORMING"
              : ratingSpread >= 18
                ? "HIGH"
                : ratingSpread >= 10
                  ? "MEDIUM"
                  : "LOW";

          const marketState =
            fieldSize === 0
              ? "FIELD LOADING"
              : pricedCount >= Math.max(1, Math.floor(fieldSize * 0.75))
                ? "LIVE"
                : pricedCount > 0
                  ? "PARTIAL"
                  : "PENDING";

          const edgeiqPriceState =
            fieldSize === 0
              ? "FIELD LOADING"
              : edgeiqPriceCount >= Math.max(1, Math.floor(fieldSize * 0.75))
                ? "AVAILABLE"
                : edgeiqPriceCount > 0
                  ? "PARTIAL"
                  : "PENDING";

          const marketCoverage = fieldSize ? `${pricedCount}/${fieldSize}` : "0/0";
          const edgeiqCoverage = fieldSize ? `${edgeiqPriceCount}/${fieldSize}` : "0/0";

          const raceRiskLines = [
            fieldSize >= 14 ? "Large field increases traffic and variance." : "Field size is manageable.",
            pressureRead === "HIGH" ? "Early pressure profile may affect settling positions." : "Early pressure profile is controlled.",
            marketState === "LIVE" ? "Market data is available for race comparison." : "Market data is still forming.",
            ratingSpread !== null && ratingSpread >= 18 ? "Wide rating spread across the field." : "Ratings are within a normal race range.",
          ];

          const investigationRows = [
            commandRatingRows[0]
              ? { label: "Today Rating Reference", item: commandRatingRows[0].item, value: renderMetricValue(commandRatingRows[0].rating, 1) }
              : null,
            commandLastStartRows[0]
              ? { label: "Fastest Last Start", item: commandLastStartRows[0].item, value: renderMetricValue(commandLastStartRows[0].rating, 1) }
              : null,
            commandPeakRows[0]
              ? { label: "Historical Peak Reference", item: commandPeakRows[0].item, value: renderMetricValue(commandPeakRows[0].rating, 1) }
              : null,
            commandTrajectoryRows[0]
              ? { label: "Trajectory Reference", item: commandTrajectoryRows[0].item, value: renderMetricValue(commandTrajectoryRows[0].score, 0) }
              : null,
          ].filter((entry): entry is { label: string; item: EnrichedRunner; value: string } => !!entry);

          const commandBox = (label: string, value: string, note?: string) => (
            <div
              style={{
                border: "1px solid rgba(80,120,180,.24)",
                borderRadius: 10,
                padding: "10px 12px",
                background: "rgba(5,12,22,.76)",
                minHeight: 58,
                display: "grid",
                gap: 4,
                alignContent: "center",
              }}
            >
              <span style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 900, textTransform: "uppercase", letterSpacing: ".07em" }}>
                {label}
              </span>
              <strong style={{ color: "#f8fafc", fontSize: 13, fontWeight: 1000, letterSpacing: ".02em" }}>
                {value || "FORMING"}
              </strong>
              {note ? <em style={{ color: "#94a3b8", fontSize: 10.5, fontStyle: "normal" }}>{note}</em> : null}
            </div>
          );

          return (
            <div style={{ display: "grid", gap: 10 }}>
              <section style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 12, padding: 10, background: "rgba(8,15,28,.72)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
                  <strong style={{ color: "#f8fafc", fontSize: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>
                    Race DNA
                  </strong>
                  <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 800 }}>
                    populated from field structure, ratings, pace profile and live race files
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(130px, 1fr))", gap: 8 }}>
                  {commandBox("Race Shape", raceShapeRead)}
                  {commandBox("Tempo", tempoRead)}
                  {commandBox("Pressure", pressureRead, `${leaderCount} forward runners`)}
                  {commandBox("Late Speed", lateSpeedRead, `${backmarkerCount} late profiles`)}
                  {commandBox("Variance", varianceRead, ratingSpread === null ? "rating spread pending" : `${renderMetricValue(ratingSpread, 1)} point spread`)}
                  {commandBox("Field", fieldSize ? `${fieldSize} runners` : "FIELD LOADING")}
                </div>
              </section>

              <section style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 12, padding: 10, background: "rgba(8,15,28,.72)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
                  <strong style={{ color: "#f8fafc", fontSize: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>
                    Market And Price State
                  </strong>
                  <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 800 }}>
                    descriptive only — no betting instruction
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(150px, 1fr))", gap: 8 }}>
                  {commandBox("Market State", marketState, `${marketCoverage} runners priced`)}
                  {commandBox("EDGEiQ Price", edgeiqPriceState, `${edgeiqCoverage} runners priced`)}
                  {commandBox("Rating Average", ratingAvg === null ? "FORMING" : renderMetricValue(ratingAvg, 1))}
                  {commandBox("Rating Spread", ratingSpread === null ? "FORMING" : renderMetricValue(ratingSpread, 1))}
                </div>
              </section>

              <section style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 12, padding: 10, background: "rgba(8,15,28,.72)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
                  <strong style={{ color: "#f8fafc", fontSize: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>
                    Race Characteristics
                  </strong>
                  <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 800 }}>
                    evidence summary before runner investigation
                  </span>
                </div>

                <div style={{ display: "grid", gap: 6 }}>
                  {raceRiskLines.map((line, index) => (
                    <div
                      key={`command-race-characteristic-${index}`}
                      style={{
                        border: "1px solid rgba(51,65,85,.72)",
                        borderRadius: 9,
                        padding: "8px 10px",
                        color: "#f8fafc",
                        background: "rgba(2,6,23,.48)",
                        fontSize: 12,
                        fontWeight: 800,
                      }}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </section>

              <section style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 12, padding: 10, background: "rgba(8,15,28,.72)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
                  <strong style={{ color: "#f8fafc", fontSize: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>
                    Investigation Starting Points
                  </strong>
                  <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 800 }}>
                    not selections — shortcuts into runner intelligence
                  </span>
                </div>

                {investigationRows.length ? (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 8 }}>
                    {investigationRows.map((entry) => {
                      const key = runnerRowKey(entry.item.row);
                      return (
                        <button
                          type="button"
                          key={`command-investigation-${entry.label}-${key}`}
                          onClick={() => {
                            setSelectedKey(key);
                            setIntelMode("RUNNERS");
                            setRunnerSubMode("PROFILE");
                            setDrawerOpen(true);
                          }}
                          style={{
                            border: "1px solid rgba(80,120,180,.32)",
                            borderRadius: 10,
                            padding: "10px 12px",
                            background: "rgba(5,12,22,.78)",
                            cursor: "pointer",
                            textAlign: "left",
                            display: "grid",
                            gap: 5,
                          }}
                        >
                          <span style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 900, textTransform: "uppercase", letterSpacing: ".07em" }}>
                            {entry.label}
                          </span>
                          <strong style={{ color: "#f8fafc", fontSize: 13, fontWeight: 1000 }}>
                            {horse(entry.item.row)}
                          </strong>
                          <span style={{ color: "#f8fafc", fontSize: 12, fontWeight: 900 }}>
                            {entry.value}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ color: "#f8fafc", fontSize: 12, fontWeight: 800 }}>
                    Runner investigation points are forming from the available race files.
                  </div>
                )}
              </section>
            </div>
          );
        })()}
      </section>
      ) : null}
'''

text = text[:start] + "\n" + new_command + text[end:]
path.write_text(text, encoding="utf-8")
print("[COMMAND_REBUILD] RaceIntelligenceScreen.tsx updated")
