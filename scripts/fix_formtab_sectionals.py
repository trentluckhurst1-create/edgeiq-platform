from pathlib import Path

path = Path(r".\src\components\FormTab.tsx")
text = path.read_text(encoding="utf-8")

replacements = {
'''<div><span>Run Style</span><strong className="standard-above">SUSTAINER</strong></div>''':
'''<div><span>Run Style</span><strong className="standard-above">{selected?.run_style_cluster || selected?.sectional_profile || "-"}</strong></div>''',

'''<div><span>Late Power</span><strong className="standard-above">ELITE</strong></div>''':
'''<div><span>Late Power</span><strong className="standard-above">{selected?.late_power_index != null ? selected.late_power_index.toFixed(0) : "-"}</strong></div>''',

'''<div><span>Tempo Fit</span><strong>SUITS RACE SHAPE</strong></div>''':
'''<div><span>Tempo Fit</span><strong>{selected?.tempo_fit || "-"}</strong></div>''',

'''<div><span>Burst Rating</span><strong>8.4</strong></div>''':
'''<div><span>Burst Rating</span><strong>{selected?.burst_index != null ? selected.burst_index.toFixed(0) : "-"}</strong></div>''',

'''<div><span>Fatigue Risk</span><strong className="standard-below">LOW</strong></div>''':
'''<div><span>Fatigue Risk</span><strong className="standard-below">{selected?.fatigue_risk_index != null ? selected.fatigue_risk_index.toFixed(0) : "-"}</strong></div>''',

'''<div><span>Sectional Weapon</span><strong className="standard-above">HIGH SPEED MID/FINAL</strong></div>''':
'''<div><span>Sectional Weapon</span><strong className="standard-above">{selected?.sectional_weapon_score != null ? selected.sectional_weapon_score.toFixed(0) : "-"}</strong></div>'''
}

for old, new in replacements.items():
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("FORMTAB PLACEHOLDERS REPLACED WITH REAL SECTIONAL DATA")
