from pathlib import Path

path = Path(r".\src\components\FormTab.tsx")

text = path.read_text(encoding="utf-8")

old = '      <section className="edgeiq-form-tab terminal-panel-stack">\n        <div className="edgeiq-form-rail terminal-card runner-tile-grid" aria-label="Race runners">'

new = '      <section className="edgeiq-form-tab terminal-panel-stack">\n        {/* RUNNER TILE RAIL REMOVED - RUNNER DECISION LADDER NOW PRIMARY */}\n\n        <div className="edgeiq-form-layout edgeiq-form-layout-full">'

text = text.replace(old, new)

old2 = '''
        </div>

        <div className="edgeiq-form-layout">
'''

new2 = '''
        </div>
'''

text = text.replace(old2, new2)

path.write_text(text, encoding="utf-8")

print("=" * 60)
print("FORMTAB DUPLICATE RUNNER RAIL REMOVED")
print("RIGHT PANEL NOW DEDICATED TO SELECTED RUNNER INTELLIGENCE")
print("=" * 60)
