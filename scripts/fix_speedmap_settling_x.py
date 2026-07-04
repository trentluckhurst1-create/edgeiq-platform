from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

old = '''function xPosition(row: RawRow, index: number): number {
  const raw = runStyleText(row);
  const score =
    num(row.settling_score) ??
    num(row.early_speed_score) ??
    num(row.barrier_speed) ??
    num(row.speed_score);

  if (num(row.map_x_pct) !== null) return clamp(num(row.map_x_pct) ?? 50, 4, 82);

  if (raw.includes("LEAD") || raw.includes("FRONT")) return clamp(4 + index * 2, 3, 18);
  if (raw.includes("PACE") || raw.includes("HANDY") || raw.includes("STALK")) return clamp(18 + index * 3, 12, 42);
  if (raw.includes("OFF")) return clamp(38 + index * 2.5, 30, 56);
  if (raw.includes("MID")) return clamp(48 + index * 2.5, 42, 68);
  if (raw.includes("BACK") || raw.includes("CLOS") || raw.includes("REAR") || raw.includes("LATE")) return clamp(66 + index * 2, 58, 82);

  if (score !== null) {
    return clamp(82 - score * 0.9, 6, 82);
  }

  return clamp(48 + index * 2, 36, 72);
}'''

new = '''function xPosition(row: RawRow, index: number): number {
  const raw = runStyleText(row);
  const score =
    num(row.settling_score) ??
    num(row.early_speed_score) ??
    num(row.barrier_speed) ??
    num(row.speed_score);

  if (num(row.map_x_pct) !== null) return clamp(num(row.map_x_pct) ?? 50, 4, 86);

  const jitter = ((index * 7) % 11) - 5;

  if (raw.includes("LEAD") || raw.includes("FRONT")) {
    return clamp(5 + jitter * 0.8, 3, 12);
  }

  if (raw.includes("PACE") || raw.includes("HANDY") || raw.includes("STALK")) {
    return clamp(22 + jitter * 1.4, 14, 32);
  }

  if (raw.includes("OFF")) {
    return clamp(38 + jitter * 1.5, 32, 48);
  }

  if (raw.includes("MID")) {
    return clamp(52 + jitter * 1.7, 44, 64);
  }

  if (raw.includes("BACK") || raw.includes("CLOS") || raw.includes("REAR") || raw.includes("LATE")) {
    return clamp(72 + jitter * 1.8, 64, 84);
  }

  if (score !== null) {
    return clamp(86 - score * 1.05, 5, 86);
  }

  return clamp(52 + jitter * 1.5, 44, 64);
}'''

if old not in text:
    raise SystemExit("Could not find xPosition block. No changes made.")

text = text.replace(old, new)

old_fill = '''                <div className={`racenet-band-fill ${runner ? bandClass(runner.band) : "empty"}`} />'''

new_fill = '''                <div
                  className={`racenet-band-fill ${runner ? bandClass(runner.band) : "empty"}`}
                  style={runner ? { width: `${clamp(runner.xPct + 10, 12, 95)}%` } : undefined}
                />'''

if old_fill not in text:
    raise SystemExit("Could not find band fill line. No changes made.")

text = text.replace(old_fill, new_fill)

path.write_text(text, encoding="utf-8")
print("SETTLING X + PARTIAL BAND FILL FIX APPLIED")
