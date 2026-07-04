from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

if 'edgeiq-speedmap-v2.css' not in text:
    text = 'import "./edgeiq-speedmap-v2.css";\n' + text

path.write_text(text, encoding="utf-8")

print("IMPORTED SPEEDMAP V2 CSS")
