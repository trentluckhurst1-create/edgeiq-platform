from pathlib import Path

adapters = [
    "ConnectionAdapter.ts",
    "TrackAdapter.ts",
    "WeatherAdapter.ts",
    "SectionalsAdapter.ts",
    "MarketAdapter.ts",
]

for name in adapters:
    path = Path("src/edgeiq-os/services/adapters") / name
    text = path.read_text(encoding="utf-8")

    if 'from "../feed-context"' not in text:
        text = text.replace(
            'import type { IntelligenceAdapter } from "./AdapterTypes";',
            'import { getActiveRaceContext, findFirstActiveRaceRow } from "../feed-context";\nimport { loadBundledCsv, pick } from "../feed-loader";\nimport type { IntelligenceAdapter } from "./AdapterTypes";'
        )

    source_line = next((line for line in text.splitlines() if "_SOURCE" in line or "SOURCE" in line), "")
    source_value = ""
    if '"' in source_line:
        source_value = source_line.split('"')[1]

    const_name = name.replace(".ts", "")
    key_map = {
        "ConnectionAdapter.ts": ("connections", "Connections", "CONNECTIONS", "connection_narrative", "Connections read"),
        "TrackAdapter.ts": ("track", "Track Intelligence", "TRACK", "track_intelligence_comment_v2_1", "Track read"),
        "WeatherAdapter.ts": ("weather", "Weather", "WEATHER", "weather_summary", "Weather read"),
        "SectionalsAdapter.ts": ("sectionals", "Sectionals", "SECTIONALS", "sectional_comment", "Sectional read"),
        "MarketAdapter.ts": ("market", "Market", "MARKET", "market_comment", "Market read"),
    }

    key, label, category, summary_field, title = key_map[name]

    text = f'''import {{ getActiveRaceContext, findFirstActiveRaceRow }} from "../feed-context";
import {{ loadBundledCsv, pick }} from "../feed-loader";
import type {{ IntelligenceAdapter }} from "./AdapterTypes";

export const {const_name.upper()}_SOURCE = "{source_value}";

export const {const_name}: IntelligenceAdapter = {{
  key: "{key}",
  label: "{label}",
  buildModuleOutput: () => {{
    const feed = loadBundledCsv({const_name.upper()}_SOURCE);
    const context = getActiveRaceContext();
    const row = findFirstActiveRaceRow(feed.rows, context);

    if (!feed.loaded || !row) {{
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
            summary: `No active-race row found for ${{context.track}} R${{context.raceNo}} in {source_value}.`,
            confidence: 30,
            importance: 80,
            status: "PARTIAL",
          }},
        ],
        feedHealth: {{
          key: "{key}",
          label: "{label}",
          status: "PARTIAL",
          freshness: `Loaded ${{feed.rows.length}} rows; no active-race match`,
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
          summary: pick(row, ["{summary_field}"], "{label} active-race summary unavailable."),
          confidence: 75,
          importance: 85,
          status: "READY",
        }},
      ],
      feedHealth: {{
        key: "{key}",
        label: "{label}",
        status: "READY",
        freshness: `Loaded ${{feed.rows.length}} rows; active race ${{context.track}} R${{context.raceNo}}`,
      }},
    }};
  }},
}};
'''
    path.write_text(text, encoding="utf-8")

print("[EDGEIQ] Active race context wired into remaining adapters")
