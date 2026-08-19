from pathlib import Path

path = Path(r".\scripts\build_live_speed_map_engine_v2.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
'    hist = historic_lookup.get(horse_key) or historic_lookup.get(key(horse))',
'''    hist = historic_lookup.get(horse_key)
    if hist is None:
        hist = historic_lookup.get(key(horse))'''
)

text = text.replace(
'    sec = sectional_lookup.get(horse_key) or sectional_lookup.get(key(horse))',
'''    sec = sectional_lookup.get(horse_key)
    if sec is None:
        sec = sectional_lookup.get(key(horse))'''
)

path.write_text(text, encoding="utf-8")

print("PATCHED ambiguous pandas Series lookup")
