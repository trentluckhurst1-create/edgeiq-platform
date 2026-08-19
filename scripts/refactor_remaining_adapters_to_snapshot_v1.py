from pathlib import Path

adapters_dir = Path("src/edgeiq-os/services/adapters")

specs = {
    "ConnectionAdapter.ts": ["ConnectionAdapter", "CONNECTIONADAPTER_SOURCE", "connections", "connections", "Connections", "CONNECTIONS", "connection_narrative", "Connection summary unavailable.", "Connections read", "/data/edgeiq_connection_intelligence_v2_1.csv"],
    "TrackAdapter.ts": ["TrackAdapter", "TRACKADAPTER_SOURCE", "track", "track", "Track Intelligence", "TRACK", "track_intelligence_comment_v2_1", "Track intelligence unavailable.", "Track read", "/data/edgeiq_live_track_intelligence_v2_1.csv"],
    "WeatherAdapter.ts": ["WeatherAdapter", "WEATHERADAPTER_SOURCE", "weather", "weather", "Weather", "WEATHER", "weather_summary", "Weather summary unavailable.", "Weather read", "/data/edgeiq_live_weather_feed_v1.csv"],
    "SectionalsAdapter.ts": ["SectionalsAdapter", "SECTIONALSADAPTER_SOURCE", "sectionals", "sectionals", "Sectionals", "SECTIONALS", "sectional_comment", "Sectional summary unavailable.", "Sectional read", "/data/edgeiq_live_sectional_intelligence_v1.csv"],
    "MarketAdapter.ts": ["MarketAdapter", "MARKETADAPTER_SOURCE", "market", "market", "Market", "MARKET", "market_comment", "Market comment unavailable.", "Market read", "/data/edgeiq_market_intelligence_v1.csv"],
}

for filename, spec in specs.items():
    const_name, source_const, snapshot_key, key, label, category, field, fallback, title, source = spec
    text = f'''import {{ pick }} from "../feed-loader";
import {{ buildIntelligenceSnapshot }} from "../intelligence-snapshot";
import type {{ IntelligenceAdapter }} from "./AdapterTypes";

export const {source_const} = "{source}";

export const {const_name}: IntelligenceAdapter = {{
  key: "{key}",
  label: "{label}",
  buildModuleOutput: () => {{
    const snapshot = buildIntelligenceSnapshot();
    const rows = snapshot.{snapshot_key};
    const row = rows[0];

    if (!row) {{
      return {{
        key: "{key}",
        label: "{label}",
        category: "{category}",
        status: "PARTIAL",
        confidence: 30,
        importance: 80,
        evidence: [
          {{
            id: "{key}-active-race-gap",
            category: "{category}",
            title: "{label} active race gap",
            summary: `No {label} rows found for ${{snapshot.context.track}} R${{snapshot.context.raceNo}}.`,
            confidence: 30,
            importance: 80,
            status: "PARTIAL",
          }},
        ],
        feedHealth: {{
          key: "{key}",
          label: "{label}",
          status: "PARTIAL",
          freshness: `Snapshot active race ${{snapshot.context.track}} R${{snapshot.context.raceNo}}; no match`,
        }},
      }};
    }}

    return {{
      key: "{key}",
      label: "{label}",
      category: "{category}",
      status: "READY",
      confidence: 75,
      importance: 85,
      evidence: [
        {{
          id: "{key}-active-race",
          category: "{category}",
          title: "{title}",
          summary: pick(row, ["{field}"], "{fallback}"),
          confidence: 75,
          importance: 85,
          status: "READY",
        }},
      ],
      feedHealth: {{
        key: "{key}",
        label: "{label}",
        status: "READY",
        freshness: `Snapshot ${{snapshot.context.track}} R${{snapshot.context.raceNo}}; ${{rows.length}} rows`,
      }},
    }};
  }},
}};
'''
    (adapters_dir / filename).write_text(text, encoding="utf-8")

print("[EDGEIQ] Remaining adapters refactored to IntelligenceSnapshot")
