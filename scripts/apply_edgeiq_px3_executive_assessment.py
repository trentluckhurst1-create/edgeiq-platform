from pathlib import Path

path = Path(r".\src\components\workspaces\RaceCommandWorkspace.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(" Â· ", " · ")

old = '''  const executiveSummary = `${selectedRaceLabel} is assessed through EDGEiQ's race intelligence framework using current ratings, tactical position, surface evidence, market alignment and confidence signals. The briefing below separates opportunity, risk and context so the user can understand the race before making any decision.`;'''

new = '''  const executiveSummary = `${selectedRaceLabel} profiles as a ${raceShapeText || "developing"} race with ${racePacePressure || "pending"} pressure expected. ${topRated ? horse(topRated.row) : "The highest-rated runner"} leads the current EDGEiQ assessment, while ${bestValue ? horse(bestValue.row) : "market overlay signals"} remain the primary value reference. Surface conditions are assessed as ${headerCondition || "pending"}, with tactical position, rating strength and market alignment forming the core evidence base.`;'''

if old not in text:
    raise SystemExit("[PX3_EXECUTIVE] Could not find executive summary block")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("[PX3_EXECUTIVE] Executive assessment upgraded")
