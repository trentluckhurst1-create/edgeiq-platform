from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''                <span className={`edgeiq-dna-confidence ${runner.confidence.toLowerCase().replace(/\\s+/g, "-")}`}>
                  {runner.confidence}
                </span>

                <span className="edgeiq-run-style-tag">
                  {runner.archetype}
                </span>''',
'''                <span className="edgeiq-dna-confidence" title={`DNA confidence: ${runner.confidence}`}>
                  {runner.confidence === "HIGH" ? "●●●" : runner.confidence === "MEDIUM" ? "●●○" : runner.confidence === "LOW" ? "●○○" : "○○○"}
                </span>

                <span className="edgeiq-run-style-tag">
                  {runner.mapPosition}
                </span>'''
)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("SPEED MAP TEXT CLEANED")
print("REMOVED MEDIUM / ARCHETYPE UNDER HORSE NAME")
print("DNA + STYLE MOVED TO RIGHT SIDE")
print("=" * 80)
