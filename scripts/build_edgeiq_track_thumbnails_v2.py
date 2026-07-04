from pathlib import Path
from PIL import Image

src = Path("public/assets/tracks")
out = src / "thumbs"
out.mkdir(parents=True, exist_ok=True)

W, H = 230, 76

for p in src.glob("*.png"):
    if p.parent.name == "thumbs":
        continue

    img = Image.open(p).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    canvas = Image.new("RGBA", (W, H), (2, 5, 8, 0))
    img.thumbnail((W - 8, H - 8), Image.LANCZOS)

    x = (W - img.width) // 2
    y = (H - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    canvas.save(out / p.name)

print(f"EDGEIQ_TRACK_THUMBNAILS_REBUILT={len(list(out.glob('*.png')))}")
