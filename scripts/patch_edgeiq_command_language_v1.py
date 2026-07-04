from pathlib import Path

p = Path(r".\src\components\RaceIntelligenceScreen.tsx")

text = p.read_text(encoding="utf-8")

replacements = {
    "EDGEIQ TOP CALL":"EDGEiQ TOP CALL",
    "Positive Signals":"Supporting Factors",
    "Risk Signals":"Risk Factors",
    "Why We Like It":"Key Positives",
    "What Could Beat It":"Key Risks",
    "EDGEiQ View":"EDGEiQ Assessment",
    "CONNECTION DNA":"CONNECTION INSIGHTS",
    "Connection DNA":"Connection Insights",
    "No positive signals loaded.":"No supporting factors loaded.",
    "Runner Profile DNA":"Runner Profile",
    ">DNA<":">Runner Profile<"
}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text, encoding="utf-8")

print("[COMMAND_LANGUAGE_UI_PATCH] COMPLETE")
