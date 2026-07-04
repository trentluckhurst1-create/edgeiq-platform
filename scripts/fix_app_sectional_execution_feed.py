from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
app = root / "src" / "App.tsx"
text = app.read_text(encoding="utf-8")

backup = app.with_suffix(".tsx.sectional_fix_backup")
backup.write_text(text, encoding="utf-8")

# 1) Remove any broken early executionFeedRows useMemo.
text = re.sub(
    r"\n\s*const executionFeedRows\s*=\s*useMemo<[^>]+>\(\(\)\s*=>\s*\{.*?\n\s*\},\s*\[[^\]]*\]\);\n",
    "\n",
    text,
    flags=re.S,
)

text = re.sub(
    r"\n\s*const executionFeedRows\s*=\s*useMemo\(\(\)\s*=>\s*\{.*?\n\s*\},\s*\[[^\]]*\]\);\n(?=.*currentRace)",
    "\n",
    text,
    flags=re.S,
    count=1,
)

# 2) Ensure sectional tempo CSV is loaded if App has the normal loadCsvOptional pattern.
if "edgeiq_sectional_tempo_engine_v1.csv" not in text:
    marker = 'loadCsvOptional("/data/'
    # Insert near other data loads inside useEffect by finding a suitable Promise/all area is risky.
    # Safer: add a standalone effect after state declaration if sectionalTempoRows state exists.
    pass

# 3) Ensure LiveExecutionTerminal rows cast, if prop exists.
text = re.sub(
    r"<LiveExecutionTerminal([^>]*?)rows=\{executionFeedRows\}([^>]*)>",
    r"<LiveExecutionTerminal\1rows={executionFeedRows as any}\2>",
    text,
)

# 4) Insert clean executionFeedRows after currentRace useMemo block.
if "const executionFeedRows = useMemo(() => {" not in text:
    m = re.search(r"(const currentRace\s*=\s*useMemo\(\(\)\s*=>\s*\{.*?\n\s*\},\s*\[[^\]]*\]\);)", text, flags=re.S)
    if not m:
        raise SystemExit("Could not find currentRace useMemo block. Inspect App.tsx manually.")
    insert = r'''

  const executionFeedRows = useMemo(() => {
    return (currentRace?.rows ?? []).map((row) => ({
      horse: row.horse,
      track: row.track,
      race_no: String(row.raceNo ?? ""),
      race_time: row.raceTime ?? "",
      sportsbet_price: row.marketPrice !== null && row.marketPrice !== undefined ? String(row.marketPrice) : "",
      rated_price: row.ratedPrice !== null && row.ratedPrice !== undefined ? String(row.ratedPrice) : "",
      overlay_pct: row.edgePct !== null && row.edgePct !== undefined ? String(row.edgePct) : "",
      execution_action: runnerDecision(row),
      jockey: row.jockey ?? "",
      trainer: row.trainer ?? "",
      mobile_silk_image: row.silkUrl ?? "",

      sectional_profile: row.sectional_profile ?? "",
      sectional_edge_tier: row.sectional_edge_tier ?? "",
      sectional_strength_score: row.sectional_strength_score !== null && row.sectional_strength_score !== undefined ? String(row.sectional_strength_score) : "",
      sectional_overlay_signal: row.sectional_overlay_signal ?? "",
      sectional_confidence: row.sectional_confidence ?? "",
      tempo_role: row.tempo_role ?? "",
      projected_tempo_shape: row.projected_tempo_shape ?? "",
      pace_collapse_risk: row.pace_collapse_risk ?? "",
      tempo_fit: row.tempo_fit ?? "",
      tempo_edge_score: row.tempo_edge_score !== null && row.tempo_edge_score !== undefined ? String(row.tempo_edge_score) : "",
      tempo_edge_grade: row.tempo_edge_grade ?? "",
      sectional_weapon_score: row.sectional_weapon_score !== null && row.sectional_weapon_score !== undefined ? String(row.sectional_weapon_score) : "",
      late_power_index: row.late_power_index !== null && row.late_power_index !== undefined ? String(row.late_power_index) : "",
      burst_index: row.burst_index !== null && row.burst_index !== undefined ? String(row.burst_index) : "",
      sustain_index: row.sustain_index !== null && row.sustain_index !== undefined ? String(row.sustain_index) : "",
      fatigue_risk_index: row.fatigue_risk_index !== null && row.fatigue_risk_index !== undefined ? String(row.fatigue_risk_index) : "",
      run_style_cluster: row.run_style_cluster ?? "",
    }));
  }, [currentRace]);
'''
    text = text[:m.end()] + insert + text[m.end():]

app.write_text(text, encoding="utf-8")
print("PATCHED App.tsx executionFeedRows placement and LiveExecutionTerminal cast")
print(f"Backup saved: {backup}")
