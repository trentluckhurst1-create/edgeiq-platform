from pathlib import Path

path = Path(r".\src\components\FormTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''  selectedCareerStats?: CareerStats | null;
};''',
'''  selectedCareerStats?: CareerStats | null;
  speedRows?: Record<string, any>[];
};'''
)

text = text.replace(
'''  selectedCareerStats = null,
}: Props): React.ReactElement {''',
'''  selectedCareerStats = null,
  speedRows = [],
}: Props): React.ReactElement {'''
)

text = text.replace(
'''  const action = actionFor(selected);''',
'''  const action = actionFor(selected);

  const selectedSpeed = speedRows.find((row) =>
    String(row.horse ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "") ===
    String(selected?.horse ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "")
  );

  const projectedSpd = selectedSpeed?.projected_spd ?? "-";
  const settlingBand = selectedSpeed?.settling_band ?? "-";
  const settlingConfidence = selectedSpeed?.confidence ?? "-";
  const archetype = selectedSpeed?.archetype ?? "-";'''
)

text = text.replace(
'''          <div><span>Confidence</span><strong>{selected?.modelConfidenceScore != null ? selected.modelConfidenceScore.toFixed(0) : "-"}</strong></div>
          <div><span>Run Style</span><strong>{selected?.run_style_cluster || selected?.sectional_profile || "-"}</strong></div>''',
'''          <div><span>Map SPD</span><strong>{projectedSpd}</strong></div>
          <div><span>Settling</span><strong>{settlingBand}</strong></div>
          <div><span>DNA Conf</span><strong>{settlingConfidence}</strong></div>
          <div><span>Archetype</span><strong>{archetype}</strong></div>
          <div><span>Confidence</span><strong>{selected?.modelConfidenceScore != null ? selected.modelConfidenceScore.toFixed(0) : "-"}</strong></div>
          <div><span>Run Style</span><strong>{selected?.run_style_cluster || selected?.sectional_profile || "-"}</strong></div>'''
)

path.write_text(text, encoding="utf-8")

print("FORMTAB NOW SHOWS SPEED MAP DNA / SETTLING DATA")
