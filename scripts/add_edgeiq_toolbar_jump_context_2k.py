from pathlib import Path

root = Path.cwd()
shell = root / "src/components/shell/EdgeiqOsShell.tsx"

text = shell.read_text(encoding="utf-8")

if "<span>Jump</span>" not in text:
    text = text.replace(
        '''<span>Rail</span>
            <strong>{toolbarContext.rail || railLabel}</strong>''',
        '''<span>Rail</span>
            <strong>{toolbarContext.rail || railLabel}</strong>
            <span>Jump</span>
            <strong>{toolbarContext.jump || "Pending"}</strong>'''
    )

shell.write_text(text, encoding="utf-8")
print("[EDGEIQ_OS_JUMP_CONTEXT] toolbar jump context added")
