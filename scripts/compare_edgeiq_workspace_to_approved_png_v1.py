from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs" / "product-specification" / "EDGEIQ_APPROVED_UI_REBUILD"
APPROVED_DIR = SPEC_DIR / "approved-pngs"
OUT_DIR = ROOT / "docs" / "full-product-implementation" / "screenshots" / "approved-ui-rebuild"


def rms(diff: Image.Image) -> float:
    stat = ImageStat.Stat(diff)
    squares = sum(value ** 2 for value in stat.rms)
    return (squares / len(stat.rms)) ** 0.5


def material_boxes(diff: Image.Image, threshold: int = 42, tile: int = 24) -> list[dict[str, int]]:
    rgb = diff.convert("RGB")
    width, height = rgb.size
    px = rgb.load()
    boxes: list[dict[str, int]] = []
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            count = 0
            total = 0
            for yy in range(y, min(y + tile, height)):
                for xx in range(x, min(x + tile, width)):
                    r, g, b = px[xx, yy]
                    total += 1
                    if max(r, g, b) >= threshold:
                        count += 1
            if total and count / total >= 0.18:
                boxes.append(
                    {
                        "left": x,
                        "top": y,
                        "right": min(x + tile, width),
                        "bottom": min(y + tile, height),
                    }
                )
    return boxes


def compare(workspace: str, rendered: Path, approved: Path, out_prefix: Path) -> dict[str, object]:
    approved_image = Image.open(approved).convert("RGB")
    rendered_image = Image.open(rendered).convert("RGB")
    if rendered_image.size != approved_image.size:
        rendered_image = rendered_image.resize(approved_image.size)

    overlay = Image.blend(approved_image, rendered_image, 0.5)
    diff = ImageChops.difference(approved_image, rendered_image)
    amplified = diff.point(lambda value: min(255, value * 3))

    side_by_side = Image.new("RGB", (approved_image.width * 2, approved_image.height), "white")
    side_by_side.paste(approved_image, (0, 0))
    side_by_side.paste(rendered_image, (approved_image.width, 0))

    boxes = material_boxes(diff)
    boxed = rendered_image.copy()
    draw = ImageDraw.Draw(boxed)
    for box in boxes[:120]:
        draw.rectangle([box["left"], box["top"], box["right"], box["bottom"]], outline=(255, 0, 0), width=1)

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    overlay_path = out_prefix.with_name(out_prefix.name + "_OVERLAY.png")
    diff_path = out_prefix.with_name(out_prefix.name + "_DIFF.png")
    side_path = out_prefix.with_name(out_prefix.name + "_SIDE_BY_SIDE.png")
    material_path = out_prefix.with_name(out_prefix.name + "_MATERIAL_REGIONS.png")
    overlay.save(overlay_path)
    amplified.save(diff_path)
    side_by_side.save(side_path)
    boxed.save(material_path)

    metric = {
        "workspace": workspace,
        "approved": str(approved),
        "rendered": str(rendered),
        "overlay": str(overlay_path),
        "diff": str(diff_path),
        "side_by_side": str(side_path),
        "material_regions_image": str(material_path),
        "rms_difference": round(rms(diff), 3),
        "material_region_count": len(boxes),
        "material_regions_sample": boxes[:40],
        "visual_status": "REVIEW_REQUIRED",
        "note": "A low metric is not a pass by itself; inspect structure, content, spacing, and prohibited content.",
    }
    report_path = out_prefix.with_name(out_prefix.name + "_COMPARISON.json")
    report_path.write_text(json.dumps(metric, indent=2), encoding="utf-8")
    return metric


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, help="Workspace key such as 01_HOME")
    parser.add_argument("--rendered", required=True, help="Rendered screenshot path")
    parser.add_argument("--approved", default=None, help="Approved PNG path; defaults to approved-pngs")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Output directory")
    args = parser.parse_args()

    workspace = args.workspace.upper()
    rendered = Path(args.rendered)
    if args.approved:
        approved = Path(args.approved)
    else:
        matches = list(APPROVED_DIR.rglob(f"{workspace}_APPROVED.png"))
        approved = matches[0] if matches else APPROVED_DIR / f"{workspace}_APPROVED.png"
    if not rendered.exists():
        raise SystemExit(f"Rendered screenshot not found: {rendered}")
    if not approved.exists():
        raise SystemExit(f"Approved PNG not found: {approved}")
    out_prefix = Path(args.out_dir) / workspace
    result = compare(workspace, rendered, approved, out_prefix)
    print(json.dumps(result, indent=2))
    print("EDGEIQ_APPROVED_UI_VISUAL_COMPARISON_PASS")


if __name__ == "__main__":
    main()
