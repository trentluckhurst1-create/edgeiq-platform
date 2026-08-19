from pathlib import Path

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

old = '''  const raceClarity = firstText(intelligenceCard, ["race_clarity_band_v1"], "—").replace(/_/g, " ");
  const expectedTempo = firstText(intelligenceCard, ["expected_tempo_band_v1"], "—").replace(/_/g, " ");
  const bettingConfidence = firstText(intelligenceCard, ["betting_confidence_band_v1"], "—").replace(/_/g, " ");
  const raceStory = firstText(intelligenceCard, ["race_story_v1"], "");
  const trackProfile = `${trackCondition(header).toUpperCase()} / ${distance(header)} / ${raceClass(header)}`;
'''

new = '''  const raceClarity = firstText(intelligenceCard, ["race_clarity_band_v1"], "—").replace(/_/g, " ");
  const expectedTempo = firstText(intelligenceCard, ["expected_tempo_band_v1"], "—").replace(/_/g, " ");
  const bettingConfidence = firstText(intelligenceCard, ["betting_confidence_band_v1"], "—").replace(/_/g, " ");
  const raceStory = firstText(intelligenceCard, ["race_story_v1"], "");
  const trackProfile = header
    ? `${trackCondition(header).toUpperCase()} / ${distance(header)} / ${raceClass(header)}`
    : "—";
'''

if old not in text:
    raise SystemExit("TRACK_PROFILE_RUNTIME_BLOCK_NOT_FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("RACE_INTELLIGENCE_RUNTIME_BLANK_FIX_COMPLETE")
