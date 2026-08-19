from pathlib import Path
import re

css = Path(r".\src\edgeiq-speedmap-v2.css")
text = css.read_text(encoding="utf-8")

# Make the bar behave as one continuous strip from EARLY/0 through to projected SPD.
text = re.sub(
    r"\.edgeiq-speed-bar-wrap\s*\{[^}]*\}",
    """.edgeiq-speed-bar-wrap {
  position: relative;
  grid-column: 6 / -1;
  height: 20px;
  border-radius: 999px;
  overflow: hidden;
  background:
    repeating-linear-gradient(
      90deg,
      rgba(148, 163, 184, 0.11) 0px,
      rgba(148, 163, 184, 0.11) 1px,
      transparent 1px,
      transparent 10%
    ),
    rgba(3, 10, 18, 0.42);
}""",
    text,
    flags=re.S,
)

text = re.sub(
    r"\.edgeiq-speed-bar\s*\{[^}]*\}",
    """.edgeiq-speed-bar {
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  display: block;
  border-radius: 999px;
  min-width: 10px;
}""",
    text,
    flags=re.S,
)

text = re.sub(
    r"\.edgeiq-speed-bar\.leader,\s*\.edgeiq-speed-bar\.on-pace,\s*\.edgeiq-speed-bar\.midfield,\s*\.edgeiq-speed-bar\.backmarker\s*\{[^}]*\}",
    """.edgeiq-speed-bar.leader,
.edgeiq-speed-bar.on-pace,
.edgeiq-speed-bar.midfield,
.edgeiq-speed-bar.backmarker {
  background: linear-gradient(
    90deg,
    rgba(62, 180, 112, 0.72) 0%,
    rgba(126, 231, 149, 0.95) 100%
  );
  box-shadow:
    0 0 10px rgba(126, 231, 149, 0.18),
    inset 0 0 8px rgba(255,255,255,0.08);
}""",
    text,
    flags=re.S,
)

css.write_text(text, encoding="utf-8")

print("=" * 80)
print("SPEED MAP BAR FIXED")
print("BARS NOW RUN CONTINUOUSLY FROM 0/EARLY TO PROJECTED SPD")
print("=" * 80)
