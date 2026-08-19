
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import { describeFeedMatch } from "../feed-diagnostics";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const WEATHERADAPTER_SOURCE = "/data/edgeiq_live_weather_feed_v1.csv";

export const WeatherAdapter: IntelligenceAdapter = {
  key: "weather",
  label: "Weather",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.weather;
    const row = rows[0];

    if (!row) {
      return {
        key: "weather",
        label: "Weather",
        category: "WEATHER",
        status: "PARTIAL",
        confidence: 25,
        importance: 75,
        evidence: [{
          id: "weather-gap",
          category: "WEATHER",
          title: "Weather active race gap",
          summary: `No Weather row found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
          confidence: 25,
          importance: 75,
          status: "PARTIAL",
        }],
        feedHealth: { key: "weather", label: "Weather", status: "PARTIAL", freshness: describeFeedMatch(rows, snapshot.context, "Feed diagnostics") },
      };
    }

    const summary = pick(row, ["weather_summary"], "Weather summary unavailable.");
    const status = pick(row, ["weather_status"], "UNKNOWN");
    const completeness = pick(row, ["weather_completeness_pct"], "UNKNOWN");
    const windDirection = pick(row, ["weather_wind_direction"], "UNKNOWN");
    const windSpeed = pick(row, ["weather_wind_speed"], "UNKNOWN");
    const rain = pick(row, ["weather_rain", "rainfall"], "UNKNOWN");
    const trackCondition = pick(row, ["track_condition"], "UNKNOWN");
    const trackRating = pick(row, ["track_rating"], "UNKNOWN");
    const biasBand = pick(row, ["track_bias_band"], "UNKNOWN");

    const ready = status !== "SOURCE_GAP";

    return {
      key: "weather",
      label: "Weather",
      category: "WEATHER",
      status: ready ? "READY" : "PARTIAL",
      confidence: ready ? 72 : 35,
      importance: 76,
      evidence: [
        { id: "weather-summary", category: "WEATHER", title: `Weather - ${status}`, summary, confidence: ready ? 72 : 35, importance: 84, status: ready ? "READY" : "PARTIAL" },
        { id: "weather-wind-rain", category: "WEATHER", title: "Wind and rain", summary: `Wind ${windDirection} ${windSpeed}. Rain ${rain}.`, confidence: ready ? 70 : 35, importance: 78, status: ready ? "READY" : "PARTIAL" },
        { id: "weather-track-state", category: "WEATHER", title: "Track state", summary: `Track ${trackCondition} ${trackRating}. Bias band ${biasBand}. Weather completeness ${completeness}%.`, confidence: ready ? 68 : 35, importance: 76, status: ready ? "READY" : "PARTIAL" },
      ],
      feedHealth: { key: "weather", label: "Weather", status: ready ? "READY" : "PARTIAL", freshness: `Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; weather ${status}` },
    };
  },
};
