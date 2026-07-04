from pathlib import Path
import re

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace('"#2af5dc"','"#ffffff"')
text = text.replace('"#7dd3fc"','"#ffffff"')
text = text.replace('"#f5c451"','"#ffffff"')
text = text.replace('"#ffca4b"','"#ffffff"')
text = text.replace('"#c084fc"','"#ffffff"')

path.write_text(text,encoding="utf-8")
print("COLOUR_SIMPLIFICATION_COMPLETE")
