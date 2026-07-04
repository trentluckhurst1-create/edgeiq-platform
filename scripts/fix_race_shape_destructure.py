from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
"const [raceCard, raceFields, rated, finalRatings, history, summary, speed, silks, careerStats, fullCareer, scratchings, results, standards, bias, pacePressure, sectionalTempo] = await Promise.all([",
"const [raceCard, raceFields, rated, finalRatings, history, summary, speed, silks, careerStats, fullCareer, scratchings, results, standards, bias, pacePressure, raceShape, sectionalTempo] = await Promise.all(["
)

path.write_text(text, encoding="utf-8")
print("PATCHED Promise.all destructure with raceShape")
