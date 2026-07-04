from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

replacements = {
    "Loaded Evidence":"Available",
    "Limited Evidence":"Limited",
    "NO EVIDENCE":"Unavailable",
    "Evidence Quality":"Coverage",
    "Evidence Confidence":"Confidence",
    "Market Context":"Market",
    "Market source unavailable":"Awaiting Feed",
    "Source-aware":"",
    "Source state":"Feed",
    "Operational Status":"",
    "How EDGEiQ Reads A Race":"",
    "Evidence First":"",
    "Always Learning":"",
    "Independent":"",
    "Explainable":""
}

for old,new in replacements.items():
    text = text.replace(old,new)

path.write_text(text,encoding="utf-8")
print("PREMIUM_COPY_CLEANUP_COMPLETE")
