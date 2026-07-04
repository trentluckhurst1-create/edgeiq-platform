from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

old = """  const sectionalBias = topSectional
    ? `${topSectional.runStyleCluster || "SECTIONAL"} EDGE`
    : "NO SECTIONAL MATCH";

  const preferredArchetype =
    topSectional?.runStyleCluster || "UNKNOWN";

  const realTempoShape =
    topSectional?.projectedTempoShape || expectedTempo;

  const realCollapseRisk =
    topSectional?.paceCollapseRisk || collapseRisk;
"""

new = """  const sectionalBias =
    String(raceShape?.preferred_archetype || "").trim() ||
    (topSectional
      ? `${topSectional.runStyleCluster || "SECTIONAL"} EDGE`
      : "NO SECTIONAL MATCH");

  const preferredArchetype =
    String(raceShape?.preferred_archetype || "").trim() ||
    topSectional?.runStyleCluster ||
    "UNKNOWN";

  const realTempoShape =
    String(raceShape?.projected_tempo_shape || "").trim() ||
    topSectional?.projectedTempoShape ||
    expectedTempo;

  const realCollapseRisk =
    String(raceShape?.pace_collapse_risk || "").trim() ||
    topSectional?.paceCollapseRisk ||
    collapseRisk;

  const pressureIndex =
    Number(raceShape?.pressure_index ?? 0);

  const shapeConfidence =
    String(raceShape?.shape_confidence || "LOW");

  const topSectionalHorse =
    String(raceShape?.top_sectional_horse || "").trim();

  const topSectionalScore =
    Number(raceShape?.top_sectional_score ?? 0);
"""

if old not in text:
    raise SystemExit("TACTICAL BLOCK NOT FOUND")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("PATCHED SpeedMapTab TO USE REAL RACE SHAPE ENGINE")
