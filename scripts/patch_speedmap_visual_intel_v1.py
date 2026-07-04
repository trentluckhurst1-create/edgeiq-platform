from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''type Runner = {
  horse: string;
  saddlecloth: string;
  jockey: string;
  barrier: number;
  spd: number;
  silkUrl: string;
  mapPosition: string;
  isScratched: boolean;
};''',
'''type Runner = {
  horse: string;
  saddlecloth: string;
  jockey: string;
  barrier: number;
  spd: number;
  silkUrl: string;
  mapPosition: string;
  confidence: string;
  archetype: string;
  settlingNote: string;
  isScratched: boolean;
};'''
)

text = text.replace(
'''    isScratched: boolish(val(row, ["is_scratched", "isScratched", "scratched"])),''',
'''    confidence: val(row, ["confidence", "confidence_tier", "shape_confidence"]) || "LOW",
    archetype: val(row, ["archetype", "run_style_archetype", "settling_archetype"]) || style,
    settlingNote: val(row, ["settling_note", "note", "comment"]) || "",
    isScratched: boolish(val(row, ["is_scratched", "isScratched", "scratched"])),'''
)

text = text.replace(
'''          <div className="edgeiq-speed-table">''',
'''          <div className="edgeiq-speed-legend">
            <span><i className="leader"></i>Leader</span>
            <span><i className="on-pace"></i>On pace</span>
            <span><i className="midfield"></i>Midfield</span>
            <span><i className="backmarker"></i>Backmarker</span>
          </div>

          <div className="edgeiq-speed-table">'''
)

text = text.replace(
'''            <span className="scale">100</span>''',
'''            <span className="scale">100</span>
            <span>DNA</span>
            <span>Style</span>'''
)

text = text.replace(
'''                <span className="edgeiq-speed-bar-wrap">
                  <i
                    className={`edgeiq-speed-bar ${runner.mapPosition.replace(/\\s+/g, "-").toLowerCase()}`}
                    style={{ width: `${runner.spd}%` }}
                  />
                </span>''',
'''                <span className="edgeiq-speed-bar-wrap">
                  <i
                    className={`edgeiq-speed-bar ${runner.mapPosition.replace(/\\s+/g, "-").toLowerCase()}`}
                    style={{ width: `${Math.max(4, Math.min(100, runner.spd * 6.5))}%` }}
                    title={runner.settlingNote}
                  />
                </span>

                <span className={`edgeiq-dna-confidence ${runner.confidence.toLowerCase().replace(/\\s+/g, "-")}`}>
                  {runner.confidence}
                </span>

                <span className="edgeiq-run-style-tag">
                  {runner.archetype}
                </span>'''
)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("SPEEDMAP COMPONENT POLISH PATCH COMPLETE")
print("=" * 80)
