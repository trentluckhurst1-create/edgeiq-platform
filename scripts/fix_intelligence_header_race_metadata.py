from pathlib import Path

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

insert_after = '''function horse(row: Row): string {
  return text(row.horse || row.horseName || row.runner || row.runner_name);
}
'''

helper = '''function distance(row: Row): string {
  const d = text(row.distance || row.race_distance || row.dist);
  return d ? `${d}m`.replace("mm", "m") : "—";
}

function raceClass(row: Row): string {
  return text(row.race_class_clean || row.race_class || row.class || row.raceClass || row.grade || row.race_grade) || "—";
}

function trackCondition(row: Row): string {
  return text(row.track_condition || row.condition || row.going || row.trackCondition) || "—";
}

'''

if helper.strip() not in text:
    text = text.replace(insert_after, insert_after + "\n" + helper)

old = '''          <h2 style={{ margin: "6px 0 4px", fontSize: 24 }}>
            {track(header)} R{raceNo(header)}
          </h2>
          <p style={{ margin: 0, color: "#bfd0ea" }}>
            Live Runner Board is the primary source. V8 and Bet Quality are sidecars only.
          </p>
'''

new = '''          <h2 style={{ margin: "6px 0 4px", fontSize: 24 }}>
            {track(header)} R{raceNo(header)}
          </h2>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0" }}>
            <span style={{ border: "1px solid rgba(80,120,180,.35)", borderRadius: 999, padding: "5px 10px", background: "rgba(16,24,42,.85)", color: "#cbd5e1", fontWeight: 900 }}>
              DIST {distance(header)}
            </span>
            <span style={{ border: "1px solid rgba(80,120,180,.35)", borderRadius: 999, padding: "5px 10px", background: "rgba(16,24,42,.85)", color: "#cbd5e1", fontWeight: 900 }}>
              CLASS {raceClass(header)}
            </span>
            <span style={{ border: "1px solid rgba(91,229,169,.35)", borderRadius: 999, padding: "5px 10px", background: "rgba(18,80,62,.25)", color: "#bbf7d0", fontWeight: 900 }}>
              TRACK {trackCondition(header)}
            </span>
          </div>

          <p style={{ margin: 0, color: "#bfd0ea" }}>
            Live Runner Board is the primary source. V8 and Bet Quality are sidecars only.
          </p>
'''

if old not in text:
    raise SystemExit("HEADER_BLOCK_NOT_FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("INTELLIGENCE_HEADER_DISTANCE_CLASS_CONDITION_COMPLETE")
