from pathlib import Path
import re

path = Path("scripts/audit_edgeiq_current_day_source_inventory_v1.py")
s = path.read_text(encoding="utf-8")

s = s.replace('DISPLAY_TRACK = "PAKENHAM SYNTHETIC"', '''def detect_display_track() -> str:
    universe_path = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
    if universe_path.exists():
        try:
            frame = pd.read_csv(universe_path, dtype=str, keep_default_na=False, low_memory=False).fillna("")
            if "race_date" in frame.columns and "track" in frame.columns:
                today_rows = frame[frame["race_date"].astype(str).str[:10] == TODAY].copy()
                if not today_rows.empty:
                    tracks = today_rows["track"].map(norm_track)
                    tracks = tracks[tracks != ""]
                    if not tracks.empty:
                        return str(tracks.mode().iloc[0])
        except Exception:
            pass
    return "PAKENHAM SYNTHETIC"


DISPLAY_TRACK = detect_display_track()''')

# Replace Pakenham-specific count naming with selected meeting naming in output fields where safe.
s = s.replace('"pakenham_synthetic_row_count": 0,', '"selected_track_total_row_count": 0,')
s = s.replace('base_row["pakenham_synthetic_row_count"]', 'base_row["selected_track_total_row_count"]')

path.write_text(s, encoding="utf-8")
print("Updated audit helper to dynamically detect DISPLAY_TRACK from current-day meeting universe")
