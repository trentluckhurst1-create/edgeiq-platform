from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

utils_dir = root / "src" / "utils"
utils_dir.mkdir(exist_ok=True)

track_maps = utils_dir / "trackMaps.ts"
track_maps.write_text('''export function getTrackMapSlug(trackName: string): string {
  const clean = String(trackName || "").toUpperCase().trim();

  const aliases: Record<string, string> = {
    "BALLARAT SYNTHETIC": "ballarat_synthetic",
    "PAKENHAM SYNTHETIC": "pakenham_synthetic",
    "PAKENHAM / TYNONG": "pakenham_tynong",
    "PAKENHAM TYNONG": "pakenham_tynong",
    "GEELONG SYNTHETIC": "geelong_synthetic",
    "GEELONG TURF": "geelong_turf",
    "MOONEE VALLEY": "moonee_valley",
    "YARRA VALLEY": "yarra_valley",
    "STONY CREEK": "stony_creek",
    "SWAN HILL": "swan_hill",
    "GREAT WESTERN": "great_western",
    "MT WYCHEPROOF": "mt_wycheproof",
    "ST ARNAUD": "st_arnaud",
  };

  return aliases[clean] || clean.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}
''', encoding="utf-8")

home = root / "src" / "screens" / "HomeScreen.tsx"
home_text = home.read_text(encoding="utf-8")
if 'import { getTrackMapSlug } from "../utils/trackMaps";' not in home_text:
    home_text = home_text.replace('import React from "react";', 'import React from "react";\nimport { getTrackMapSlug } from "../utils/trackMaps";')

home_text = re.sub(
    r'\nconst getHomeTrackMapSlug = \(trackName: string\) => \{.*?\n\};',
    '',
    home_text,
    flags=re.S
)
home_text = home_text.replace("getHomeTrackMapSlug(meeting.trackName)", "getTrackMapSlug(meeting.trackName)")
home.write_text(home_text, encoding="utf-8")

meetings = root / "src" / "screens" / "MeetingsScreen.tsx"
meetings_text = meetings.read_text(encoding="utf-8")
if 'import { getTrackMapSlug } from "../utils/trackMaps";' not in meetings_text:
    meetings_text = meetings_text.replace('import React from "react";', 'import React from "react";\nimport { getTrackMapSlug } from "../utils/trackMaps";')

meetings_text = re.sub(
    r'\n  const getMeetingSlug = \(trackName: string\) => \{.*?\n  \};',
    '',
    meetings_text,
    flags=re.S
)
meetings_text = meetings_text.replace("getMeetingSlug(meeting?.trackName || \"\")", "getTrackMapSlug(meeting?.trackName || \"\")")
meetings.write_text(meetings_text, encoding="utf-8")

print("[TRACK_MAP_SLUG_REFACTOR] complete")
