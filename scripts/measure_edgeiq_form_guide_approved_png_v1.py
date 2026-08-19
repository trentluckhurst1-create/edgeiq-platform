from __future__ import annotations
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]
APPROVED_CANDIDATES = [
    ROOT / "docs/full-product-implementation/screenshots/approved-ui-rebuild/05_FORM_GUIDE_APPROVED.png",
    ROOT / "docs/full-product-implementation/screenshots/final-live-runtime/05_FORM_GUIDE_APPROVED.png",
    ROOT / "docs/product-specification/EDGEIQ_APPROVED_UI_REBUILD/approved-pngs/EDGEiQ_APPROVED_TABS/05_FORM_GUIDE_APPROVED.png",
]
EXACT_DIR = ROOT / "docs/full-product-implementation/screenshots/form-guide-exact"
SPEC_DIR = ROOT / "docs/product-specification"
MEASURE_OUT = SPEC_DIR / "FORM_GUIDE_APPROVED_PIXEL_MEASUREMENT_V1.json"
INVENTORY_OUT = SPEC_DIR / "FORM_GUIDE_APPROVED_PIXEL_MEASUREMENT_V1.csv"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()

def load_image(path: Path):
    from PIL import Image
    return Image.open(path).convert("RGB")

def dominant_colours(image, limit=14):
    small = image.resize((384, 256))
    counter = Counter()
    for r, g, b in small.getdata():
        # quantise to 8px buckets for stable token extraction
        key = (round(r / 8) * 8, round(g / 8) * 8, round(b / 8) * 8)
        counter[key] += 1
    total = sum(counter.values()) or 1
    rows = []
    for (r, g, b), count in counter.most_common(limit):
        rows.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "rgb": [r, g, b], "share": round(count / total, 5)})
    return rows

def edge_bounds(image):
    w, h = image.size
    pixels = image.load()
    def is_content(x, y):
        r, g, b = pixels[x, y]
        # approved screen is white; faint grey page edges count as content
        return not (r > 248 and g > 248 and b > 248)
    xs = []
    ys = []
    step = 2
    for y in range(0, h, step):
        for x in range(0, w, step):
            if is_content(x, y):
                xs.append(x); ys.append(y)
    if not xs:
        return {"left": 0, "top": 0, "right": w, "bottom": h}
    return {"left": min(xs), "top": min(ys), "right": max(xs), "bottom": max(ys)}

def scan_lines(image):
    w, h = image.size
    pixels = image.load()
    vertical = []
    horizontal = []
    for x in range(w):
        hits = 0
        for y in range(h):
            r, g, b = pixels[x, y]
            if r < 238 or g < 242 or b < 248:
                hits += 1
        if hits > h * 0.09:
            vertical.append(x)
    for y in range(h):
        hits = 0
        for x in range(w):
            r, g, b = pixels[x, y]
            if r < 238 or g < 242 or b < 248:
                hits += 1
        if hits > w * 0.09:
            horizontal.append(y)
    def compress(values):
        groups = []
        current = []
        for v in values:
            if not current or v <= current[-1] + 1:
                current.append(v)
            else:
                groups.append(current); current = [v]
        if current: groups.append(current)
        return [round(sum(g)/len(g)) for g in groups]
    return {"vertical": compress(vertical), "horizontal": compress(horizontal)}

def main():
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    EXACT_DIR.mkdir(parents=True, exist_ok=True)
    existing = [p for p in APPROVED_CANDIDATES if p.exists()]
    if not existing:
        raise SystemExit("No approved FORM GUIDE PNG found")
    records = []
    for p in existing:
        image = load_image(p)
        records.append({
            "path": str(p),
            "name": p.name,
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
            "width": image.size[0],
            "height": image.size[1],
        })
    chosen = existing[0]
    chosen_hash = records[0]["sha256"]
    mismatches = [r for r in records if r["sha256"] != chosen_hash]
    if mismatches:
        raise SystemExit(f"Approved PNG hash mismatch: {mismatches}")
    image = load_image(chosen)
    copied = EXACT_DIR / "05_FORM_GUIDE_APPROVED.png"
    copy2(chosen, copied)
    measurement = {
        "status": "FORM_GUIDE_APPROVED_PNG_MEASURED",
        "chosen_source": str(chosen),
        "copied_source": str(copied),
        "sha256": chosen_hash,
        "canvas": {"width": image.size[0], "height": image.size[1]},
        "content_bounds": edge_bounds(image),
        "dominant_colours": dominant_colours(image),
        "rule_scan": scan_lines(image),
        "candidate_pngs": records,
    }
    MEASURE_OUT.write_text(json.dumps(measurement, indent=2), encoding="utf-8")
    with INVENTORY_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "name", "bytes", "sha256", "width", "height"])
        writer.writeheader(); writer.writerows(records)
    print(json.dumps({"status": measurement["status"], "canvas": measurement["canvas"], "sha256": chosen_hash, "copied": str(copied)}, indent=2))

if __name__ == "__main__":
    main()
