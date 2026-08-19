from pathlib import Path
import re

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

# Remove broken icon glyphs / mojibake from product shell and homepage
bad_tokens = [
    "â™ž", "â™™", "â™¢", "â—Ž", "â—œ", "â—‡", "â—Œ", "â–£", "â†—", "â†ª",
    "âš–", "âŒ•", "â„¢", "â€”", "â€“", "Â", "Ã", "�"
]
for token in bad_tokens:
    text = text.replace(token, "")

# Clean button/navigation copy
text = text.replace(" Enter Terminal", "Enter Terminal")
text = text.replace(" View Today's Meetings", "View Today's Meetings")
text = text.replace("Open Meeting ", "Open Meeting")
text = text.replace("View Meeting ", "View Meeting")
text = text.replace("RACE WORKSPACE", "WORKSPACE")

# Remove icon slots from nav tuples
text = re.sub(r'\["(RACE|FIELD|MAP|INSIGHTS|MARKET|RESULTS)",\s*"[^"]*"\]', r'["\1", ""]', text)

# Premium homepage language
text = text.replace(
    "A professional racing intelligence terminal for race shape, ratings, market alignment, connections and runner evidence.",
    "Adaptive racing intelligence for race shape, ratings, market alignment and runner assessment."
)

text = text.replace(
    "EDGEiQ is a decision-support platform, not a race explanation service. It helps users understand how a race is likely to be run, where the evidence is strongest, and which runners deserve deeper analysis.",
    "Not tips. Not noise. A professional race-reading platform built to show how the race sets up."
)

# Remove internal homepage concepts
remove_phrases = [
    "Operational Status",
    "How EDGEiQ Reads A Race",
    "Evidence First",
    "Data before opinion.",
    "Explainable",
    "Transparent race intelligence.",
    "Independent",
    "No paid promotion or tipping noise.",
    "Always Learning",
    "Models adapt as the data improves.",
    "Data",
    "Engine",
    "Gear Intelligence",
    "Gear changes and debutants.",
    "Market Alignment",
    "Fair prices versus the market.",
]

for phrase in remove_phrases:
    text = text.replace(phrase, "")

# Clean duplicated spaces left by removal
text = re.sub(r'[ \t]{2,}', ' ', text)
text = re.sub(r'\n{3,}', '\n\n', text)

path.write_text(text, encoding="utf-8", newline="\n")
print("[HOME_RESCUE_COPY_AND_ENCODING_COMPLETE]")
