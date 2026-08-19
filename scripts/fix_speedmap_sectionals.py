from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

anchor = """  const beneficiaries = runners.filter((r) => r.beneficiary).length;
  const disadvantaged = runners.filter((r) => r.disadvantaged).length;
"""

insert = """

  const sectionallyMapped = plotted.filter(
    (r: any) =>
      Number(r.sectionalWeaponScore ?? 0) > 0
  );

  const topSectional = [...sectionallyMapped].sort(
    (a: any, b: any) =>
      Number(b.sectionalWeaponScore ?? 0) -
      Number(a.sectionalWeaponScore ?? 0)
  )[0];

  const sectionalBias = topSectional
    ? `${topSectional.runStyleCluster || "SECTIONAL"} EDGE`
    : "NO SECTIONAL MATCH";

  const preferredArchetype =
    topSectional?.runStyleCluster || "UNKNOWN";

  const realTempoShape =
    topSectional?.projectedTempoShape || expectedTempo;

  const realCollapseRisk =
    topSectional?.paceCollapseRisk || collapseRisk;
"""

text = text.replace(anchor, anchor + insert)

text = text.replace(
    "FAST FINISHERS ADVANTAGE",
    "{sectionalBias}"
)

text = text.replace(
    '{collapseRisk === "HIGH" ? "PACE MELTDOWN" : expectedTempo}',
    '{realCollapseRisk === "HIGH" ? "PACE MELTDOWN" : realTempoShape}'
)

text = text.replace(
    '{collapseRisk === "HIGH" ? "SWOOPERS" : "ON-PACE"}',
    '{preferredArchetype}'
)

path.write_text(text, encoding="utf-8")

print("SPEEDMAP PLACEHOLDERS REPLACED WITH REAL SECTIONAL LOGIC")
