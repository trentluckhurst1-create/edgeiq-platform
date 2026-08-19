from pathlib import Path
import re

file = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")

text = file.read_text(encoding="utf-8")

# Remove any remaining standalone AssessmentJourney component.
text = re.sub(
    r'^\s*<AssessmentJourney\s+journey=\{assessmentJourney\}\s*/>\s*$',
    '',
    text,
    flags=re.MULTILINE
)

# Collapse excessive blank lines.
text = re.sub(r'\n{3,}', '\n\n', text)

file.write_text(text, encoding="utf-8")

print("[EDGEIQ] Removed orphan AssessmentJourney component")
