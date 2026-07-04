from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "const fieldByHorse = new Map<string, CsvRow>();",
    "const fieldByHorse = new Map<string, any>();"
)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("TYPESCRIPT MAP TYPE FIXED")
print("=" * 80)
