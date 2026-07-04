from pathlib import Path
import re

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

patterns = [
    r"\.edgeiq-speed-bar\.leader\s*\{[^}]*\}",
    r"\.edgeiq-speed-bar\.on-pace\s*\{[^}]*\}",
    r"\.edgeiq-speed-bar\.midfield\s*\{[^}]*\}",
    r"\.edgeiq-speed-bar\.backmarker\s*\{[^}]*\}",
]

replacement = """
.edgeiq-speed-bar.leader,
.edgeiq-speed-bar.on-pace,
.edgeiq-speed-bar.midfield,
.edgeiq-speed-bar.backmarker {
  background: linear-gradient(
    90deg,
    rgba(105, 208, 140, 0.72) 0%,
    rgba(126, 231, 149, 0.95) 100%
  );
  box-shadow:
    0 0 10px rgba(126, 231, 149, 0.18),
    inset 0 0 8px rgba(255,255,255,0.08);
}
"""

for pattern in patterns:
    text = re.sub(pattern, "", text, flags=re.S)

if ".edgeiq-speed-bar.leader," not in text:
    text += "\n" + replacement + "\n"

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("UNIFIED SETTLING BAND COLOURS APPLIED")
print("=" * 80)
