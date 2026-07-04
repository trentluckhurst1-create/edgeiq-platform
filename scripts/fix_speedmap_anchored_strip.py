from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''function bandOf(row: RawRow): MapRunner["band"] {
  const raw = runStyleText(row);

  if (raw.includes("LEAD") || raw.includes("FRONT") || raw.includes("PACE") || raw.includes("HANDY") || raw.includes("STALK")) {
    return "ON_PACE";
  }

  if (raw.includes("BACK") || raw.includes("CLOS") || raw.includes("REAR") || raw.includes("LATE")) {
    return "BACKMARKER";
  }

  if (raw.includes("MID") || raw.includes("OFF")) {
    return "MIDFIELD";
  }

  return "MIDFIELD";
}''',
'''function bandOf(row: RawRow): MapRunner["band"] {
  const raw = runStyleText(row);

  if (raw.includes("LEAD") || raw.includes("FRONT") || raw.includes("PACE") || raw.includes("HANDY") || raw.includes("STALK")) {
    return "ON_PACE";
  }

  if (raw.includes("BACK") || raw.includes("CLOS") || raw.includes("REAR") || raw.includes("LATE")) {
    return "BACKMARKER";
  }

  if (raw.includes("MID") || raw.includes("OFF")) {
    return "MIDFIELD";
  }

  return "MIDFIELD";
}'''
)

text = text.replace(
'''                <div
                  className={`racenet-band-fill ${runner ? bandClass(runner.band) : "empty"}`}
                  style={runner ? { left: `${clamp(runner.xPct, 4, 88)}%` } : undefined}
                />''',
'''                <div
                  className={`racenet-band-fill ${runner ? bandClass(runner.band) : "empty"}`}
                  style={runner ? { width: `${clamp(92 - runner.xPct, 8, 88)}%` } : undefined}
                />'''
)

text = text.replace(
'''                    style={{ right: "34px" }}''',
'''                    style={{ right: "34px" }}'''
)

text = text.replace(
'''function bandLabel(band: MapRunner["band"]): string {
  if (band === "ON_PACE") return "On Pace";
  if (band === "BACKMARKER") return "Backmarker";
  if (band === "UNKNOWN") return "No Data";
  return "Midfield";
}''',
'''function bandLabel(band: MapRunner["band"]): string {
  if (band === "ON_PACE") return "Leader / On Pace";
  if (band === "BACKMARKER") return "Backmarker";
  if (band === "UNKNOWN") return "No Data";
  return "Midfield";
}'''
)

path.write_text(text, encoding="utf-8")
print("ANCHORED STRIP TSX FIX APPLIED")
