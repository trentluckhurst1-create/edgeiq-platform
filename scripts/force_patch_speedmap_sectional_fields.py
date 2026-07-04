from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

# Force-add sectional fields immediately after the isScratched property inside mapRunner return object.
text2 = re.sub(
    r"(isScratched:\s*boolish\(row\.is_scratched\),)",
    r"""\1

    runStyleCluster: val(row, ["run_style_cluster", "sectional_profile"]),
    tempoFit: val(row, ["tempo_fit"]),
    sectionalWeaponScore: maybeNum(val(row, ["sectional_weapon_score", "sectional_strength_score"])) ?? 0,
    latePowerIndex: maybeNum(val(row, ["late_power_index"])) ?? 0,
    fatigueRiskIndex: maybeNum(val(row, ["fatigue_risk_index"])) ?? 0,
    projectedTempoShape: val(row, ["projected_tempo_shape"]),
    paceCollapseRisk: val(row, ["pace_collapse_risk"]),""",
    text,
    count=1
)

if text2 == text:
    raise SystemExit("NO PATCH MADE: isScratched pattern not found")

path.write_text(text2, encoding="utf-8")
print("PATCHED SpeedMapTab mapRunner sectional return fields")
