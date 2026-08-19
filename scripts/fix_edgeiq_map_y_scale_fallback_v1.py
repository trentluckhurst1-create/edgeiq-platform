from pathlib import Path
path=Path('src/components/RaceIntelligenceScreen.tsx')
text=path.read_text(encoding='utf-8')
old='''  const explicitMapYValues = activeMapRows
    .map((item) => firstNum(item.row, ["map_y_px"]))
    .filter((value): value is number => value !== null && Number.isFinite(value));
'''
new='''  const explicitMapYValues = activeMapRows
    .map((item) => firstNum(item.mapEnrichment, ["map_y_px"]) ?? firstNum(item.row, ["map_y_px"]))
    .filter((value): value is number => value !== null && Number.isFinite(value));
'''
if old not in text:
    raise SystemExit('expected map_y block missing')
path.write_text(text.replace(old,new,1),encoding='utf-8')
print('MAP_Y_SCALE_FALLBACK_APPLIED')
