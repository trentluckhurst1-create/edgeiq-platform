from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

start_marker = '{fullHistoryRunner ? (() => {'
end_marker = '\n\n </section>'

start = text.find(start_marker)
if start == -1:
    raise SystemExit("fullHistoryRunner start marker not found")

end = text.find(end_marker, start)
if end == -1:
    raise SystemExit("closing section marker after fullHistoryRunner not found")

block = text[start:end]
inner = block[len(start_marker):]
inner = inner.rsplit("})() : null}", 1)[0].strip()

component = f'''type Row = Record<string, any>;

type CareerHistoryModalProps = {{
  fullHistoryRunner: any;
  setFullHistoryRunner: any;
  firstNum: any;
  historyFinishText: any;
  historyRatingValue: any;
  horse: any;
  firstText: any;
  renderMetricValue: any;
  historyRunKey: any;
  formatHistoryDate: any;
  historyDateText: any;
  historyTrackText: any;
  historyDistanceText: any;
  historyClassText: any;
  historyGoingText: any;
  historyJockeyText: any;
  historySpText: any;
}};

export function CareerHistoryModal({{
  fullHistoryRunner,
  setFullHistoryRunner,
  firstNum,
  historyFinishText,
  historyRatingValue,
  horse,
  firstText,
  renderMetricValue,
  historyRunKey,
  formatHistoryDate,
  historyDateText,
  historyTrackText,
  historyDistanceText,
  historyClassText,
  historyGoingText,
  historyJockeyText,
  historySpText,
}}: CareerHistoryModalProps) {{
  if (!fullHistoryRunner) return null;

{inner}
}}
'''

Path("src/components/overlays").mkdir(parents=True, exist_ok=True)
Path("src/components/overlays/CareerHistoryModal.tsx").write_text(component, encoding="utf-8")

replacement = '''<CareerHistoryModal
 fullHistoryRunner={fullHistoryRunner}
 setFullHistoryRunner={setFullHistoryRunner}
 firstNum={firstNum}
 historyFinishText={historyFinishText}
 historyRatingValue={historyRatingValue}
 horse={horse}
 firstText={firstText}
 renderMetricValue={renderMetricValue}
 historyRunKey={historyRunKey}
 formatHistoryDate={formatHistoryDate}
 historyDateText={historyDateText}
 historyTrackText={historyTrackText}
 historyDistanceText={historyDistanceText}
 historyClassText={historyClassText}
 historyGoingText={historyGoingText}
 historyJockeyText={historyJockeyText}
 historySpText={historySpText}
/>'''

text = text[:start] + replacement + text[end:]

import_line = 'import { CareerHistoryModal } from "./overlays/CareerHistoryModal";\n'
if import_line.strip() not in text:
    marker = 'import { RatingHoverTooltip } from "./overlays/RatingHoverTooltip";\n'
    if marker in text:
        text = text.replace(marker, marker + import_line, 1)
    else:
        first_import_end = text.find("\n", text.find("import "))
        text = text[:first_import_end + 1] + import_line + text[first_import_end + 1:]

path.write_text(text, encoding="utf-8")
print("[CAREER_MODAL_EXTRACT] CareerHistoryModal extracted")
