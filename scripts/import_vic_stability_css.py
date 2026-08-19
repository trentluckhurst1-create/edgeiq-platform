from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

if 'import "./edgeiq-vic-stability-pass.css";' not in text:
    text = 'import "./edgeiq-vic-stability-pass.css";\n' + text

path.write_text(text, encoding="utf-8")

print("IMPORTED VIC STABILITY CSS")
