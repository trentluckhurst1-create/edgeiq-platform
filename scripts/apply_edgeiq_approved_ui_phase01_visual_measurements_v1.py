from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import median

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs" / "product-specification" / "EDGEIQ_APPROVED_UI_REBUILD"
PNG_ROOT = SPEC_DIR / "approved-pngs"
OUTPUT_DIR = SPEC_DIR


WORKSPACES = [
    "01_HOME",
    "02_MEETINGS",
    "03_RACE_OVERVIEW",
    "04_FIELD",
    "05_FORM_GUIDE",
    "06_PERFORMANCE",
    "07_MAP",
    "08_EPI",
    "09_MARKET",
    "10_OVERVIEW",
    "11_SCRATCHINGS",
    "12_GEAR_CHANGES",
    "13_TRACK",
    "14_WEATHER",
    "15_RESULTS",
    "16_INSIGHTS",
    "17_LAB",
    "18_COMPARE",
    "19_REVIEW",
]


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


def hex_color(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb[:3])


def color_bucket(value: int) -> int:
    return max(0, min(255, round(value / 8) * 8))


def row_profile(image: Image.Image) -> list[float]:
    width, height = image.size
    px = image.convert("RGB").load()
    rows: list[float] = []
    for y in range(height):
        diffs = []
        last = px[0, y]
        for x in range(1, width):
            current = px[x, y]
            diffs.append(color_distance(last, current))
            last = current
        rows.append(sum(diffs) / max(1, len(diffs)))
    return rows


def column_profile(image: Image.Image) -> list[float]:
    width, height = image.size
    px = image.convert("RGB").load()
    cols: list[float] = []
    for x in range(width):
        diffs = []
        last = px[x, 0]
        for y in range(1, height):
            current = px[x, y]
            diffs.append(color_distance(last, current))
            last = current
        cols.append(sum(diffs) / max(1, len(diffs)))
    return cols


def boundary_candidates(values: list[float], limit: int = 16) -> list[int]:
    if not values:
        return []
    threshold = max(median(values) * 2.2, sorted(values)[int(len(values) * 0.92)])
    candidates = [i for i, value in enumerate(values) if value >= threshold]
    grouped: list[int] = []
    active: list[int] = []
    for value in candidates:
        if not active or value <= active[-1] + 2:
            active.append(value)
            continue
        grouped.append(active[len(active) // 2])
        active = [value]
    if active:
        grouped.append(active[len(active) // 2])
    return grouped[:limit]


def dominant_colors(image: Image.Image, sample_step: int = 4, limit: int = 16) -> list[dict[str, object]]:
    width, height = image.size
    pixels = image.convert("RGB").load()
    counter: Counter[tuple[int, int, int]] = Counter()
    for y in range(0, height, sample_step):
        for x in range(0, width, sample_step):
            r, g, b = pixels[x, y]
            bucket = (color_bucket(r), color_bucket(g), color_bucket(b))
            counter[bucket] += 1
    total = sum(counter.values()) or 1
    return [
        {"hex": hex_color(rgb), "rgb": list(rgb), "share": round(count / total, 4)}
        for rgb, count in counter.most_common(limit)
    ]


def find_content_bounds(image: Image.Image) -> dict[str, int]:
    width, height = image.size
    rgb = image.convert("RGB")
    bg = rgb.getpixel((0, 0))
    px = rgb.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            if color_distance(px[x, y], bg) > 22:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return {"left": 0, "top": 0, "right": width, "bottom": height}
    return {"left": min(xs), "top": min(ys), "right": max(xs), "bottom": max(ys)}


def estimate_table_rows(image: Image.Image) -> dict[str, object]:
    rows = row_profile(image)
    candidates = boundary_candidates(rows, 64)
    gaps = [b - a for a, b in zip(candidates, candidates[1:]) if 12 <= b - a <= 42]
    row_height = int(round(median(gaps))) if gaps else None
    return {"horizontal_rule_candidates": candidates, "estimated_row_height": row_height}


def measure(path: Path) -> dict[str, object]:
    image = Image.open(path)
    width, height = image.size
    rows = row_profile(image)
    cols = column_profile(image)
    x_bounds = boundary_candidates(cols)
    y_bounds = boundary_candidates(rows)
    colors = dominant_colors(image)
    light_colors = [c for c in colors if luminance(tuple(c["rgb"])) > 160]
    dark_text_colors = [c for c in colors if 20 < luminance(tuple(c["rgb"])) < 120]
    return {
        "workspace": path.stem.replace("_APPROVED", ""),
        "source_png": str(path),
        "canvas": {"width": width, "height": height},
        "content_bounds": find_content_bounds(image),
        "major_vertical_boundaries_x": x_bounds,
        "major_horizontal_boundaries_y": y_bounds,
        "left_navigation_width_estimate": x_bounds[0] if x_bounds else None,
        "top_header_height_estimate": y_bounds[0] if y_bounds else None,
        "table_measurements": estimate_table_rows(image),
        "dominant_colors": colors,
        "likely_surface_colors": light_colors[:6],
        "likely_text_colors": dark_text_colors[:6],
        "notes": [
            "Measurements are pixel-derived guides for reconstruction and visual QA.",
            "Font family cannot be identified reliably from pixels; use local approved app font and tune size/weight/line-height.",
        ],
    }


def main() -> None:
    if not PNG_ROOT.exists():
        raise SystemExit(f"Approved PNG directory missing: {PNG_ROOT}")
    png_lookup = {path.name: path for path in PNG_ROOT.rglob("*.png")}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_measurements = []
    for workspace in WORKSPACES:
        png = png_lookup.get(f"{workspace}_APPROVED.png")
        if not png or not png.exists():
            raise SystemExit(f"Missing approved PNG: {workspace}_APPROVED.png under {PNG_ROOT}")
        result = measure(png)
        all_measurements.append(result)
        out = OUTPUT_DIR / f"{workspace}_MEASUREMENTS.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"measured {png.name} -> {out.name}")

    global_tokens = {
        "source": "EDGEiQ_APPROVED_TABS.zip",
        "workspace_count": len(all_measurements),
        "canvas": {"width": 1536, "height": 1024},
        "common_dominant_colors": Counter(
            color["hex"]
            for measurement in all_measurements
            for color in measurement["dominant_colors"][:8]
        ).most_common(24),
        "left_navigation_width_estimates": {
            measurement["workspace"]: measurement["left_navigation_width_estimate"]
            for measurement in all_measurements
        },
        "top_header_height_estimates": {
            measurement["workspace"]: measurement["top_header_height_estimate"]
            for measurement in all_measurements
        },
        "table_row_height_estimates": {
            measurement["workspace"]: measurement["table_measurements"]["estimated_row_height"]
            for measurement in all_measurements
        },
    }
    (OUTPUT_DIR / "GLOBAL_VISUAL_TOKENS.json").write_text(
        json.dumps(global_tokens, indent=2),
        encoding="utf-8",
    )
    print("EDGEIQ_APPROVED_UI_VISUAL_MEASUREMENTS_PASS")


if __name__ == "__main__":
    main()
