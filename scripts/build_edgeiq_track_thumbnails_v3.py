from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
TRACK_DIR = ROOT / "public" / "assets" / "tracks"
THUMB_DIR = TRACK_DIR / "thumbs"
SUMMARY = ROOT / "public" / "data" / "edgeiq_track_thumbnails_v3_summary.csv"

THUMB_W = 320
THUMB_H = 128
PAD = 12


def content_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    rgba = image.convert("RGBA")
    alpha_box = rgba.getchannel("A").getbbox()
    if alpha_box:
        return alpha_box

    # Fallback for non-transparent source images: crop away the corner background.
    rgb = image.convert("RGB")
    bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    diff = ImageChops.difference(rgb, bg).convert("L")
    mask = diff.point(lambda px: 255 if px > 8 else 0)
    return mask.getbbox() or (0, 0, image.width, image.height)


def build_thumb(path: Path) -> dict[str, object]:
    source = Image.open(path).convert("RGBA")
    box = content_bbox(source)
    cropped = source.crop(box)

    max_w = THUMB_W - (PAD * 2)
    max_h = THUMB_H - (PAD * 2)
    scale = min(max_w / max(1, cropped.width), max_h / max(1, cropped.height))
    fitted_w = max(1, round(cropped.width * scale))
    fitted_h = max(1, round(cropped.height * scale))
    fitted = cropped.resize((fitted_w, fitted_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    x = (THUMB_W - fitted_w) // 2
    y = (THUMB_H - fitted_h) // 2
    canvas.alpha_composite(fitted, (x, y))

    out = THUMB_DIR / path.name
    canvas.save(out, "PNG", optimize=True)
    return {
        "track_image": path.name,
        "source_width": source.width,
        "source_height": source.height,
        "crop_left": box[0],
        "crop_top": box[1],
        "crop_right": box[2],
        "crop_bottom": box[3],
        "crop_width": cropped.width,
        "crop_height": cropped.height,
        "thumb_width": THUMB_W,
        "thumb_height": THUMB_H,
        "fitted_width": fitted_w,
        "fitted_height": fitted_h,
        "offset_x": x,
        "offset_y": y,
        "output": str(out.relative_to(ROOT)),
    }


def main() -> int:
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in sorted(TRACK_DIR.glob("*.png")):
        if path.parent == THUMB_DIR:
            continue
        rows.append(build_thumb(path))

    fields = [
        "track_image",
        "source_width",
        "source_height",
        "crop_left",
        "crop_top",
        "crop_right",
        "crop_bottom",
        "crop_width",
        "crop_height",
        "thumb_width",
        "thumb_height",
        "fitted_width",
        "fitted_height",
        "offset_x",
        "offset_y",
        "output",
    ]
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Track thumbnails v3 built: {len(rows)} thumbnails at {THUMB_W}x{THUMB_H}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
