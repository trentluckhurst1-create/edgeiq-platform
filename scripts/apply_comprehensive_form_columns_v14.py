from pathlib import Path

path = Path("src/edgeiq-os/race/RaceFileV3.tsx")
backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_COMPREHENSIVE_FORM_COLUMNS_20260709.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

text = text.replace(
'''<th>Cond</th>
              <th>Pos</th>
              <th>Margin</th>
              <th>SP</th>''',
'''<th>Cond</th>
              <th>Bar</th>
              <th>Wt</th>
              <th>Jockey</th>
              <th>SP</th>
              <th>Pos</th>
              <th>Margin</th>'''
)

text = text.replace(
'''<td>{clean(official.condition)}</td>
                    <td>{clean(official.finish)}</td>
                    <td>{clean(official.margin)}</td>
                    <td>{market(official.sp)}</td>''',
'''<td>{clean(official.condition)}</td>
                    <td>{clean(official.barrier)}</td>
                    <td>{weight(official.weight)}</td>
                    <td>{clean(official.jockey)}</td>
                    <td>{market(official.sp)}</td>
                    <td>{clean(official.finish)}</td>
                    <td>{clean(official.margin)}</td>'''
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Comprehensive form guide columns applied")
print(f"[EDGEIQ] checkpoint: {backup}")
