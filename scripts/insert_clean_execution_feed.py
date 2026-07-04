from pathlib import Path

path = Path(r".\src\App.tsx")

text = path.read_text(encoding="utf-8")

anchor = """  const currentRace = useMemo(
    () => currentMeeting?.races.find((race) => race.key === selectedRaceKey) ?? currentMeeting?.races[0] ?? null,
    [currentMeeting, selectedRaceKey]
  );
"""

insert = """

  const executionFeedRows = useMemo(() => {
    return (currentRace?.rows ?? []).map((row) => ({
      horse: row.horse,
      track: row.track,
      race_no: String(row.raceNo ?? ""),
      race_time: row.raceTime ?? "",

      sportsbet_price:
        row.marketPrice !== null && row.marketPrice !== undefined
          ? String(row.marketPrice)
          : "",

      rated_price:
        row.ratedPrice !== null && row.ratedPrice !== undefined
          ? String(row.ratedPrice)
          : "",

      overlay_pct:
        row.edgePct !== null && row.edgePct !== undefined
          ? String(row.edgePct)
          : "",

      execution_action: runnerDecision(row),

      jockey: row.jockey ?? "",
      trainer: row.trainer ?? "",
      mobile_silk_image: row.silkUrl ?? "",

      sectional_profile: row.sectional_profile ?? "",
      sectional_edge_tier: row.sectional_edge_tier ?? "",

      sectional_strength_score:
        row.sectional_strength_score !== null &&
        row.sectional_strength_score !== undefined
          ? String(row.sectional_strength_score)
          : "",

      sectional_overlay_signal: row.sectional_overlay_signal ?? "",
      sectional_confidence: row.sectional_confidence ?? "",

      tempo_role: row.tempo_role ?? "",
      projected_tempo_shape: row.projected_tempo_shape ?? "",
      pace_collapse_risk: row.pace_collapse_risk ?? "",
      tempo_fit: row.tempo_fit ?? "",

      tempo_edge_score:
        row.tempo_edge_score !== null &&
        row.tempo_edge_score !== undefined
          ? String(row.tempo_edge_score)
          : "",

      tempo_edge_grade: row.tempo_edge_grade ?? "",

      sectional_weapon_score:
        row.sectional_weapon_score !== null &&
        row.sectional_weapon_score !== undefined
          ? String(row.sectional_weapon_score)
          : "",

      late_power_index:
        row.late_power_index !== null &&
        row.late_power_index !== undefined
          ? String(row.late_power_index)
          : "",

      burst_index:
        row.burst_index !== null &&
        row.burst_index !== undefined
          ? String(row.burst_index)
          : "",

      sustain_index:
        row.sustain_index !== null &&
        row.sustain_index !== undefined
          ? String(row.sustain_index)
          : "",

      fatigue_risk_index:
        row.fatigue_risk_index !== null &&
        row.fatigue_risk_index !== undefined
          ? String(row.fatigue_risk_index)
          : "",

      run_style_cluster: row.run_style_cluster ?? "",
    }));
  }, [currentRace]);

"""

if insert.strip() in text:
    print("executionFeedRows already inserted")
else:
    text = text.replace(anchor, anchor + insert)
    path.write_text(text, encoding="utf-8")
    print("INSERTED CLEAN executionFeedRows AFTER currentRace")
