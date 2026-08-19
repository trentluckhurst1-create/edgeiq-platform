from pathlib import Path

adapters = Path("src/edgeiq-os/services/adapters")

files = [
    (
        "RunnerDNAAdapter.ts",
        "RunnerDNAAdapter",
        "/data/edgeiq_runner_dna_drawer_feed_v2.csv",
        "RUNNER_DNA",
        "runner-dna",
        "Runner DNA",
        [
            ("dna_band","DNA Band"),
            ("runner_summary","Runner Summary"),
            ("positive_1_factor","Primary Strength"),
            ("negative_1_factor","Primary Risk"),
            ("dna_narrative","DNA Narrative")
        ]
    ),
    (
        "ExplainabilityAdapter.ts",
        "ExplainabilityAdapter",
        "/data/edgeiq_explainability_terminal_feed_v1_2.csv",
        "GENERIC",
        "explainability",
        "Explainability",
        [
            ("why_ranked_here","Why Ranked"),
            ("runner_profile_summary","Runner Profile"),
            ("confidence_explanation","Confidence"),
            ("trend_summary","Trend"),
            ("race_shape_story","Race Shape")
        ]
    ),
]

template = r'''
import {{ loadBundledCsv, pick }} from "../feed-loader";
import type {{ IntelligenceAdapter }} from "./AdapterTypes";

export const SOURCE = "{source}";

export const {const_name}: IntelligenceAdapter = {{
  key: "{key}",
  label: "{label}",
  buildModuleOutput: () => {{
    const feed = loadBundledCsv(SOURCE);
    const row = feed.rows[0];

    if (!feed.loaded || !row) {{
      return {{
        key: "{key}",
        label: "{label}",
        category: "{category}",
        status: "ERROR",
        confidence: 0,
        importance: 90,
        evidence: [],
        feedHealth: {{
          key: "{key}",
          label: "{label}",
          status: "ERROR",
          freshness: feed.error ?? "Feed unavailable",
        }},
      }};
    }}

    return {{
      key: "{key}",
      label: "{label}",
      category: "{category}",
      status: "READY",
      confidence: 80,
      importance: 90,
      evidence: [
{evidence}
      ],
      feedHealth: {{
        key: "{key}",
        label: "{label}",
        status: "READY",
        freshness: `Loaded ${{feed.rows.length}} rows`,
      }},
    }};
  }},
}};
'''

for filename,const_name,source,category,key,label,fields in files:

    evidence=[]

    for i,(field,title) in enumerate(fields):
        evidence.append(f'''        {{
          id: "{key}-{i}",
          category: "{category}",
          title: "{title}",
          summary: pick(row, ["{field}"], "Unavailable"),
          confidence: 80,
          importance: {90-i*5},
          status: "READY",
        }}''')

    text=template.format(
        source=source,
        const_name=const_name,
        key=key,
        label=label,
        category=category,
        evidence=",\n".join(evidence)
    )

    (adapters/filename).write_text(text,encoding="utf-8")

print("[EDGEIQ] Runner DNA + Explainability adapters converted to live feed readers")
