from pathlib import Path

files = [
    Path("src/App.tsx"),
    Path("src/components/RaceIntelligenceScreen.tsx"),
]

replacements = {
    "â€”": "—",
    "â€¢": "•",
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',
    "Â": "",
    "MARKET PENDING": "AWAITING FEED",
    "Market Pending": "Awaiting Feed",
    "NO MARKET": "AWAITING FEED",
    "No Market": "Awaiting Feed",
    "SOURCE STATE": "FEED STATUS",
    "Source State": "Feed Status",
}

for path in files:
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in replacements.items():
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"[FIXED] {path}")
    else:
        print(f"[NO_CHANGE] {path}")

print("[ENCODING_AND_COPY_FIX_PASS_COMPLETE]")
