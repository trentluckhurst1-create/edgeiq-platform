from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = """        return { ...row, is_scratched: fieldRunner?.isScratched ? "1" : text(row.is_scratched), silkUrl: silkByHorse.get(key) ?? defaultSilkUrl() };
"""

new = """        return {
          ...row,
          is_scratched: fieldRunner?.isScratched ? "1" : text(row.is_scratched),
          silkUrl: silkByHorse.get(key) ?? defaultSilkUrl(),

          run_style_cluster: fieldRunner?.run_style_cluster ?? "",
          tempo_fit: fieldRunner?.tempo_fit ?? "",
          sectional_profile: fieldRunner?.sectional_profile ?? "",

          sectional_weapon_score:
            fieldRunner?.sectional_weapon_score !== null &&
            fieldRunner?.sectional_weapon_score !== undefined
              ? String(fieldRunner.sectional_weapon_score)
              : "",

          late_power_index:
            fieldRunner?.late_power_index !== null &&
            fieldRunner?.late_power_index !== undefined
              ? String(fieldRunner.late_power_index)
              : "",

          fatigue_risk_index:
            fieldRunner?.fatigue_risk_index !== null &&
            fieldRunner?.fatigue_risk_index !== undefined
              ? String(fieldRunner.fatigue_risk_index)
              : "",

          projected_tempo_shape:
            fieldRunner?.projected_tempo_shape ?? "",

          pace_collapse_risk:
            fieldRunner?.pace_collapse_risk ?? "",
        };
"""

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("ENRICHED currentSpeedRows WITH SECTIONAL DATA")
