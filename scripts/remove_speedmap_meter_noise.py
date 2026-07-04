from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''  background:
    linear-gradient(90deg, transparent 0, transparent 24.8%, rgba(120, 113, 108, 0.32) 25%, transparent 25.2%),
    linear-gradient(90deg, transparent 0, transparent 49.8%, rgba(120, 113, 108, 0.32) 50%, transparent 50.2%),
    linear-gradient(90deg, transparent 0, transparent 74.8%, rgba(120, 113, 108, 0.32) 75%, transparent 75.2%);
''',
'''  background: none;
'''
)

text = text.replace(
'''  border-top: 2px solid rgba(120, 113, 108, 0.50);
''',
'''  border-top: 1px solid rgba(120, 113, 108, 0.35);
'''
)

path.write_text(text, encoding="utf-8")
print("SPEED MAP GRID NOISE REMOVED")
