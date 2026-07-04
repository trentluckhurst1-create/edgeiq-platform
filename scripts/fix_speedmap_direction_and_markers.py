from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''        <div className="racenet-axis top">
          <span>{distanceLabel}</span>
          <span>600m</span>
          <span>400m</span>
          <span>200m</span>
          <span>Barrier</span>
        </div>
''',
''
)

text = text.replace(
'''        <div className="racenet-axis bottom">
          <span>{distanceLabel}</span>
          <span>600m</span>
          <span>400m</span>
          <span>200m</span>
          <span>Barrier</span>
        </div>
''',
''
)

text = text.replace(
'''function xPosition(row: RawRow, index: number): number {
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
}''',
'''function xPosition(row: RawRow, index: number): number {
  const raw = runStyleText(row);
  const score =
    num(row.settling_score) ??
    num(row.early_speed_score) ??
    num(row.barrier_speed) ??
    num(row.speed_score);

  const explicit = num(row.map_x_pct);
  if (explicit !== null) return clamp(92 - explicit, 6, 88);

  const jitter = ((index * 7) % 11) - 5;

  if (raw.includes("LEAD") || raw.includes("FRONT")) {
    return clamp(84 + jitter * 0.8, 78, 90);
  }

  if (raw.includes("PACE") || raw.includes("HANDY") || raw.includes("STALK")) {
    return clamp(68 + jitter * 1.4, 58, 78);
  }

  if (raw.includes("OFF")) {
    return clamp(52 + jitter * 1.5, 44, 62);
  }

  if (raw.includes("MID")) {
    return clamp(38 + jitter * 1.7, 28, 50);
  }

  if (raw.includes("BACK") || raw.includes("CLOS") || raw.includes("REAR") || raw.includes("LATE")) {
    return clamp(18 + jitter * 1.8, 8, 30);
  }

  if (score !== null) {
    return clamp(6 + score * 0.9, 8, 88);
  }

  return clamp(38 + jitter * 1.5, 28, 50);
}'''
)

path.write_text(text, encoding="utf-8")
print("DIRECTION AND AXIS MARKER FIX APPLIED")
