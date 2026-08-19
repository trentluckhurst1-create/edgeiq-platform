from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

# Add VIC-only helper after cleanTrack if it does not exist.
helper = '''
const VIC_TRACKS = new Set([
  "FLEMINGTON",
  "CAULFIELD",
  "SANDOWN",
  "SANDOWN LAKESIDE",
  "SANDOWN HILLSIDE",
  "MOONEE VALLEY",
  "MORNINGTON",
  "PAKENHAM",
  "PAKENHAM SYNTHETIC",
  "BENDIGO",
  "BALLARAT",
  "BALLARAT SYNTHETIC",
  "GEELONG",
  "WARRNAMBOOL",
  "CRANBOURNE",
  "SALE",
  "TERANG",
  "KILMORE",
  "SEYMOUR",
  "ECHUCA",
  "HAMILTON",
  "COLAC",
  "ARARAT",
  "WANGARATTA",
  "BENALLA",
  "SWAN HILL",
  "MILDURA",
  "KYNETON",
  "CAMPERDOWN",
  "CASTERTON",
  "WODONGA",
  "STAWELL",
  "WERRIBEE",
  "YARRA VALLEY",
  "YARRA GLEN",
  "BAIRNSDALE",
  "AVOCA",
  "BET365 PARK KILMORE",
  "BET365 PARK WODONGA",
  "SPORTSBET BALLARAT",
  "SPORTSBET PAKENHAM",
  "LADBROKES GEELONG",
]);

function isVicTrack(track: unknown): boolean {
  const cleaned = cleanTrack(track).toUpperCase();
  return VIC_TRACKS.has(cleaned) || cleaned.includes("FLEMINGTON") || cleaned.includes("CAULFIELD") || cleaned.includes("SANDOWN") || cleaned.includes("PAKENHAM") || cleaned.includes("BALLARAT") || cleaned.includes("GEELONG");
}
'''

if "function isVicTrack" not in text:
    marker = "function cleanTrack"
    idx = text.find(marker)
    if idx == -1:
        raise SystemExit("cleanTrack function not found")
    # Insert helper before first type/const block after helper functions by placing before formatSummary if available.
    anchor = "function formatSummary"
    if anchor in text:
        text = text.replace(anchor, helper + "\n" + anchor, 1)
    else:
        text = text[:idx] + helper + "\n" + text[idx:]

path.write_text(text, encoding="utf-8")
print("ADDED VIC TRACK FILTER HELPER")
