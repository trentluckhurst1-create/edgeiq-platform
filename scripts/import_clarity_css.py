from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

if 'import "./edgeiq-clarity-pass.css";' not in text:
    text = text.replace('import "./terminal/layout/terminal-shell.css";', 'import "./terminal/layout/terminal-shell.css";\nimport "./edgeiq-clarity-pass.css";')

path.write_text(text, encoding="utf-8")

print("IMPORTED clarity CSS")
