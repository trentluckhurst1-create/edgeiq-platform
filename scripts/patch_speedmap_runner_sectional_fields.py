from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

old = """    isScratched: boolish(row.is_scratched),
"""

new = """    isScratched: boolish(row.is_scratched),

    runStyleCluster: val(row, ["run_style_cluster", "sectional_profile"]),
    tempoFit: val(row, ["tempo_fit"]),
    sectionalWeaponScore: maybeNum(val(row, ["sectional_weapon_score", "sectional_strength_score"])) ?? 0,
    latePowerIndex: maybeNum(val(row, ["late_power_index"])) ?? 0,
    fatigueRiskIndex: maybeNum(val(row, ["fatigue_risk_index"])) ?? 0,
    projectedTempoShape: val(row, ["projected_tempo_shape"]),
    paceCollapseRisk: val(row, ["pace_collapse_risk"]),
"""

if old not in text:
    raise SystemExit("Could not find SpeedMapTab isScratched line. Run Select-String around mapRunner.")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("PATCHED SpeedMapTab runner sectional fields")
