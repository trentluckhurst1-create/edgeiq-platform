from pathlib import Path

adapters = Path("src/edgeiq-os/services/adapters")

(adapters / "ConnectionAdapter.ts").write_text(r'''
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const CONNECTIONADAPTER_SOURCE = "/data/edgeiq_connection_intelligence_v2_1.csv";

export const ConnectionAdapter: IntelligenceAdapter = {
  key: "connections",
  label: "Connections",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.connections;
    const row = rows[0];

    if (!row) {
      return {
        key: "connections",
        label: "Connections",
        category: "CONNECTIONS",
        status: "PARTIAL",
        confidence: 30,
        importance: 85,
        evidence: [{
          id: "connections-gap",
          category: "CONNECTIONS",
          title: "Connections active race gap",
          summary: `No Connections rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
          confidence: 30,
          importance: 85,
          status: "PARTIAL",
        }],
        feedHealth: { key: "connections", label: "Connections", status: "PARTIAL", freshness: "No active-race match" },
      };
    }

    const horse = pick(row, ["horse"], "Reference runner");
    const band = pick(row, ["connection_band", "connection_strength"], "UNKNOWN");
    const score = pick(row, ["connection_score"], "UNKNOWN");
    const narrative = pick(row, ["connection_narrative"], "Connection narrative unavailable.");
    const angle1 = pick(row, ["connection_angle_1"], "No primary angle");
    const angle2 = pick(row, ["connection_angle_2"], "No secondary angle");
    const angle3 = pick(row, ["connection_angle_3"], "No third angle");
    const risk = pick(row, ["connection_risk_1"], "No connection risk identified");
    const quality = pick(row, ["evidence_quality"], "UNKNOWN");

    return {
      key: "connections",
      label: "Connections",
      category: "CONNECTIONS",
      status: "READY",
      confidence: 80,
      importance: 88,
      evidence: [
        { id: "connections-narrative", category: "CONNECTIONS", title: `${horse} - Connections ${band}`, summary: `Score ${score}. ${narrative}`, confidence: 80, importance: 92, status: "READY" },
        { id: "connections-angles", category: "CONNECTIONS", title: "Connection angles", summary: `${angle1}. ${angle2}. ${angle3}.`, confidence: 78, importance: 88, status: "READY" },
        { id: "connections-risk", category: "CONNECTIONS", title: "Connection risk", summary: risk, confidence: 76, importance: 84, status: "READY" },
        { id: "connections-quality", category: "CONNECTIONS", title: "Evidence quality", summary: quality, confidence: 74, importance: 78, status: "READY" },
      ],
      feedHealth: { key: "connections", label: "Connections", status: "READY", freshness: `Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${rows.length} runners` },
    };
  },
};
''', encoding="utf-8")

(adapters / "TrackAdapter.ts").write_text(r'''
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const TRACKADAPTER_SOURCE = "/data/edgeiq_live_track_intelligence_v2_1.csv";

export const TrackAdapter: IntelligenceAdapter = {
  key: "track",
  label: "Track Intelligence",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.track;
    const row = rows[0];

    if (!row) {
      return {
        key: "track",
        label: "Track Intelligence",
        category: "TRACK",
        status: "PARTIAL",
        confidence: 30,
        importance: 85,
        evidence: [{
          id: "track-gap",
          category: "TRACK",
          title: "Track active race gap",
          summary: `No Track rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
          confidence: 30,
          importance: 85,
          status: "PARTIAL",
        }],
        feedHealth: { key: "track", label: "Track Intelligence", status: "PARTIAL", freshness: "No active-race match" },
      };
    }

    const horse = pick(row, ["horse"], "Reference runner");
    const label = pick(row, ["track_intelligence_label_v2_1"], "UNKNOWN");
    const comment = pick(row, ["track_intelligence_comment_v2_1"], "Track comment unavailable.");
    const fit = pick(row, ["track_fit_band"], "UNKNOWN");
    const score = pick(row, ["track_fit_score"], "UNKNOWN");
    const styleAlign = pick(row, ["run_style_alignment"], "UNKNOWN");
    const barrierAlign = pick(row, ["barrier_alignment"], "UNKNOWN");
    const movementAlign = pick(row, ["movement_alignment"], "UNKNOWN");
    const condition = pick(row, ["track_condition"], "UNKNOWN");
    const rail = pick(row, ["rail_position"], "UNKNOWN");

    return {
      key: "track",
      label: "Track Intelligence",
      category: "TRACK",
      status: "READY",
      confidence: 78,
      importance: 88,
      evidence: [
        { id: "track-read", category: "TRACK", title: `${horse} - ${label}`, summary: comment, confidence: 78, importance: 92, status: "READY" },
        { id: "track-fit", category: "TRACK", title: `Track fit - ${fit}`, summary: `Track fit score ${score}. Condition ${condition}. Rail ${rail}.`, confidence: 76, importance: 88, status: "READY" },
        { id: "track-alignment", category: "TRACK", title: "Track alignment", summary: `Run style ${styleAlign}. Barrier ${barrierAlign}. Movement ${movementAlign}.`, confidence: 74, importance: 84, status: "READY" },
      ],
      feedHealth: { key: "track", label: "Track Intelligence", status: "READY", freshness: `Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${rows.length} runners` },
    };
  },
};
''', encoding="utf-8")

(adapters / "WeatherAdapter.ts").write_text(r'''
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
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
        feedHealth: { key: "weather", label: "Weather", status: "PARTIAL", freshness: "No active-race match" },
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
''', encoding="utf-8")

(adapters / "SectionalsAdapter.ts").write_text(r'''
import { pick } from "../feed-loader";
import { buildIntelligenceSnapshot } from "../intelligence-snapshot";
import type { IntelligenceAdapter } from "./AdapterTypes";

export const SECTIONALSADAPTER_SOURCE = "/data/edgeiq_live_sectional_intelligence_v1.csv";

export const SectionalsAdapter: IntelligenceAdapter = {
  key: "sectionals",
  label: "Sectionals",
  buildModuleOutput: () => {
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.sectionals;
    const row = rows[0];

    if (!row) {
      return {
        key: "sectionals",
        label: "Sectionals",
        category: "SECTIONALS",
        status: "PARTIAL",
        confidence: 30,
        importance: 82,
        evidence: [{
          id: "sectionals-gap",
          category: "SECTIONALS",
          title: "Sectionals active race gap",
          summary: `No Sectionals rows found for ${snapshot.context.track} R${snapshot.context.raceNo}.`,
          confidence: 30,
          importance: 82,
          status: "PARTIAL",
        }],
        feedHealth: { key: "sectionals", label: "Sectionals", status: "PARTIAL", freshness: "No active-race match" },
      };
    }

    const horse = pick(row, ["horse_name"], "Reference runner");
    const comment = pick(row, ["sectional_comment"], "Sectional summary unavailable.");
    const status = pick(row, ["sectional_intelligence_status"], "UNKNOWN");
    const archetype = pick(row, ["sectional_archetype"], "UNKNOWN");
    const evidenceType = pick(row, ["sectional_evidence_type"], "UNKNOWN");
    const depth = pick(row, ["profile_depth_status"], "UNKNOWN");
    const runs = pick(row, ["runs_with_sectionals"], "UNKNOWN");
    const early = pick(row, ["avg_early_speed"], "UNKNOWN");
    const mid = pick(row, ["avg_mid_speed"], "UNKNOWN");
    const late = pick(row, ["avg_late_speed"], "UNKNOWN");
    const peak = pick(row, ["avg_peak_speed"], "UNKNOWN");

    return {
      key: "sectionals",
      label: "Sectionals",
      category: "SECTIONALS",
      status: "READY",
      confidence: 78,
      importance: 86,
      evidence: [
        { id: "sectionals-summary", category: "SECTIONALS", title: `${horse} - ${status}`, summary: comment, confidence: 78, importance: 90, status: "READY" },
        { id: "sectionals-archetype", category: "SECTIONALS", title: `Sectional archetype - ${archetype}`, summary: `Evidence type ${evidenceType}. Profile depth ${depth}. Runs with sectionals ${runs}.`, confidence: 76, importance: 86, status: "READY" },
        { id: "sectionals-speed-profile", category: "SECTIONALS", title: "Speed profile", summary: `Early ${early}. Mid ${mid}. Late ${late}. Peak ${peak}.`, confidence: 74, importance: 82, status: "READY" },
      ],
      feedHealth: { key: "sectionals", label: "Sectionals", status: "READY", freshness: `Snapshot ${snapshot.context.track} R${snapshot.context.raceNo}; ${rows.length} runners` },
    };
  },
};
''', encoding="utf-8")

print("[EDGEIQ] Connections, Track, Weather and Sectionals adapters enriched")
