from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

text = text.replace("height: 35px;", "height: 40px;")
text = text.replace("top: 4px;\n  bottom: 4px;", "top: 6px;\n  bottom: 6px;")
text = text.replace("height: 25px;", "height: 28px;")
text = text.replace("width: 25px;", "width: 28px;")
text = text.replace("width: 22px;", "width: 25px;")
text = text.replace("height: 22px;", "height: 25px;")
text = text.replace("font-size: 12px;", "font-size: 13px;")
text = text.replace("font-size: 11px;", "font-size: 12px;")

path.write_text(text, encoding="utf-8")
print("SPEED MAP READABILITY CSS UPDATED")
