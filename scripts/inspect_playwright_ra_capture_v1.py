from pathlib import Path

ROOT = Path.cwd()
RAW = ROOT / "outputs" / "ra_active_profile_browser_capture"

print("=" * 100)
print("PLAYWRIGHT RAW HTML VALIDATION")
print("=" * 100)

for path in RAW.glob("*.html"):

    text = path.read_text(encoding="utf-8", errors="ignore")

    print()
    print("-" * 100)
    print(path.name)
    print("LEN:", len(text))
    print("ZENEDGE:", "__zenedge" in text.lower())
    print("HORSEFULLFORM:", "HorseFullForm" in text)
    print("CAREER:", "Career" in text)
    print("JOCKEY:", "Jockey" in text)
    print("BARRIER:", "Barrier" in text)
    print()

    idx = text.lower().find("horse not found")

    if idx >= 0:
        print("HORSE NOT FOUND SNIPPET:")
        print(text[max(0, idx-500):idx+500])

    else:
        print("FIRST 3000 CHARS:")
        print(text[:3000])
