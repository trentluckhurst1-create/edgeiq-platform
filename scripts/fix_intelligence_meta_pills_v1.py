from pathlib import Path
import re

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

old = '''          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0" }}>
            <span style={{ border: "1px solid rgba(80,120,180,.35)", borderRadius: 999, padding: "5px 10px", background: "rgba(16,24,42,.85)", color: "#cbd5e1", fontWeight: 900 }}>
              DIST {distance(header)}
            </span>
            <span style={{ border: "1px solid rgba(80,120,180,.35)", borderRadius: 999, padding: "5px 10px", background: "rgba(16,24,42,.85)", color: "#cbd5e1", fontWeight: 900 }}>
              CLASS {raceClass(header)}
            </span>
            <span style={{ border: "1px solid rgba(91,229,169,.35)", borderRadius: 999, padding: "5px 10px", background: "rgba(18,80,62,.25)", color: "#bbf7d0", fontWeight: 900 }}>
              TRACK {trackCondition(header)}
            </span>
          </div>'''

new = '''          <div className="edgeiq-intel-race-meta">
            <span>{distance(header)}</span>
            {raceClass(header) !== "—" && <span>{raceClass(header)}</span>}
            <span>
              TRACK <em className={`edgeiq-condition-text ${trackCondition(header).toUpperCase().startsWith("FAST") ? "cond-fast" : trackCondition(header).toUpperCase().startsWith("GOOD") ? "cond-good" : trackCondition(header).toUpperCase().startsWith("SOFT") ? "cond-soft" : trackCondition(header).toUpperCase().startsWith("HEAVY") ? "cond-heavy" : "cond-unknown"}`}>{trackCondition(header).toUpperCase()}</em>
            </span>
          </div>'''

if old not in text:
    raise SystemExit("INTELLIGENCE_META_PILLS_BLOCK_NOT_FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("INTELLIGENCE_META_PILLS_CLEANED")
