from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

if 'import "./edgeiq-speedmap-clean.css";' not in text:
    if 'import "./edgeiq-clarity-pass.css";' in text:
        text = text.replace(
            'import "./edgeiq-clarity-pass.css";',
            'import "./edgeiq-clarity-pass.css";\nimport "./edgeiq-speedmap-clean.css";'
        )
    else:
        text = text.replace(
            'import "./terminal/layout/terminal-shell.css";',
            'import "./terminal/layout/terminal-shell.css";\nimport "./edgeiq-speedmap-clean.css";'
        )

path.write_text(text, encoding="utf-8")
print("ENSURED SPEEDMAP CSS IMPORT")
