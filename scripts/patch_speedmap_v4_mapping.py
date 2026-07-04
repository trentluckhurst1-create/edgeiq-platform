from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

replacements = {
    'const rawSpeed = num(val(row, ["speed_score", "spd", "early_speed_score", "settling_score"]));':
    'const rawSpeed = num(val(row, ["projected_spd", "speed_score", "spd", "early_speed_score", "settling_score"]));',

    'const style = pos(val(row, ["map_position", "map_style", "speed_map_bucket", "run_style", "speed_map", "map_bucket", "bucket", "position"]));':
    'const style = pos(val(row, ["settling_band", "map_position", "map_style", "speed_map_bucket", "run_style", "speed_map", "map_bucket", "bucket", "position"]));',

    'if (style === "LEADER") return 95;':
    'if (style === "LEADER") return 5;',

    'if (style === "ON PACE") return 75;':
    'if (style === "ON PACE") return 30;',

    'return 35;':
    'return 85;',

    'Math.max(1, Math.min(100, Math.round(spd)))':
    'Math.max(1, Math.min(100, Number(spd.toFixed(1))))',
}

missing = []

for old, new in replacements.items():
    if old not in text:
        missing.append(old)
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("SPEED MAP V4 MAPPING PATCH COMPLETE")
print("=" * 80)

if missing:
    print("MISSING PATTERNS:")
    for m in missing:
        print(m)
else:
    print("ALL PATTERNS PATCHED")
