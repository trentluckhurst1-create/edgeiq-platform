from pathlib import Path

path = Path('src/edgeiq-os/home/EdgeiqOsHome.tsx')
text = path.read_text(encoding='utf-8')
old = '            <div><dt>Pipeline</dt><dd>{allSystems}</dd></div>\n            <div><dt>Window</dt><dd>{pipelineStatus?.melbourne_date ?? currentDisplayDate(model)}</dd></div>'
new = '            <div><dt>Pipeline</dt><dd>{allSystems}</dd></div>\n            <div><dt>Data Discipline</dt><dd>Browser-safe product feeds</dd></div>\n            <div><dt>Window</dt><dd>{pipelineStatus?.melbourne_date ?? currentDisplayDate(model)}</dd></div>'
if old not in text:
    raise SystemExit('HOME data quality insertion point not found')
path.write_text(text.replace(old, new), encoding='utf-8')
print('EDGEIQ_HOME_DATA_DISCIPLINE_CONFORMANCE_ROW_RESTORED')
