from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

# Remove the extra style text under the horse name completely
text = re.sub(
    r'\s*<span className="edgeiq-run-style-tag">\s*\{runner\.mapPosition\}\s*</span>',
    '',
    text,
    flags=re.S
)

# Remove the DNA/style header labels
text = text.replace(
    '<span>DNA</span>\n            <span>Style</span>',
    ''
)

# Remove mini confidence dots from left side
text = re.sub(
    r'\s*<span className="edgeiq-dna-confidence".*?</span>',
    '',
    text,
    flags=re.S
)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("SPEED MAP CLEANUP COMPLETE")
print("REMOVED:")
print("- ON PACE / MIDFIELD TEXT")
print("- DNA DOTS")
print("- DNA/STYLE HEADERS")
print("=" * 80)
