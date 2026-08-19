from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs/product-specification"
MEASURE = SPEC_DIR / "FORM_GUIDE_APPROVED_PIXEL_MEASUREMENT_V1.json"
LEGACY_MEASURE = ROOT / "docs/product-specification/EDGEIQ_APPROVED_UI_REBUILD/05_FORM_GUIDE_MEASUREMENTS.json"

MD = SPEC_DIR / "FORM_GUIDE_APPROVED_PIXEL_SPEC_V1.md"
JSON_OUT = SPEC_DIR / "FORM_GUIDE_APPROVED_PIXEL_SPEC_V1.json"
TEXT_CSV = SPEC_DIR / "FORM_GUIDE_APPROVED_TEXT_SPEC_V1.csv"
GEOM_CSV = SPEC_DIR / "FORM_GUIDE_APPROVED_GEOMETRY_V1.csv"
TOKENS_CSS = SPEC_DIR / "FORM_GUIDE_APPROVED_STYLE_TOKENS_V1.css"

REGIONS = [
    {"id":"canvas", "x":0, "y":0, "w":1536, "h":1024, "role":"root", "notes":"Approved PNG canvas."},
    {"id":"left_nav", "x":0, "y":0, "w":186, "h":1024, "role":"persistent_navigation", "notes":"White left rail with EDGEiQ brand and workspace buttons."},
    {"id":"topbar", "x":186, "y":0, "w":1350, "h":66, "role":"global_header", "notes":"Product title, operating-system subtitle, date/time/status icons."},
    {"id":"content", "x":207, "y":72, "w":1310, "h":900, "role":"workspace_content", "notes":"FORM GUIDE page content area."},
    {"id":"breadcrumb", "x":208, "y":78, "w":350, "h":16, "role":"breadcrumb", "notes":"MEETINGS > FLEMINGTON > RACE 1 > FORM GUIDE."},
    {"id":"race_title", "x":208, "y":102, "w":350, "h":34, "role":"race_identity", "notes":"Race 1, race name, class badge."},
    {"id":"race_meta", "x":208, "y":144, "w":1010, "h":20, "role":"race_metadata", "notes":"Location, date, time, distance, surface, prize money, weather."},
    {"id":"subnav", "x":208, "y":170, "w":1308, "h":40, "role":"section_tabs", "notes":"Race overview through Form Guide, active blue underline on Form Guide."},
    {"id":"form_tools", "x":993, "y":221, "w":466, "h":22, "role":"form_tools", "notes":"Ratings View selector, customise columns, export."},
    {"id":"summary_table", "x":208, "y":249, "w":1308, "h":153, "role":"runner_summary_table", "notes":"16-column all-runner table with five compact runner rows."},
    {"id":"expanded_runner", "x":208, "y":414, "w":1308, "h":556, "role":"expanded_runner_card", "notes":"Selected runner profile card with blue outline."},
    {"id":"runner_header", "x":220, "y":426, "w":1245, "h":62, "role":"selected_runner_header", "notes":"Saddlecloth, silk, horse name and top metric strip."},
    {"id":"today_match", "x":218, "y":497, "w":204, "h":232, "role":"today_match_panel", "notes":"Track/distance/going/rail/tempo/pace setup with match rating."},
    {"id":"profile_matrix", "x":428, "y":497, "w":878, "h":232, "role":"horse_profile_matrix", "notes":"Career, condition, class, jockey and prep matrix with Today badges."},
    {"id":"match_insights", "x":1310, "y":497, "w":198, "h":232, "role":"match_insights", "notes":"Five selected-runner insight bullets."},
    {"id":"recent_form", "x":220, "y":742, "w":1280, "h":210, "role":"recent_form_table", "notes":"Recent form last 8 starts table plus sectional legend."},
    {"id":"footer", "x":612, "y":993, "w":850, "h":20, "role":"app_footer", "notes":"Copyright/build/data timestamp footer."},
]

TEXT = [
    ("brand", "EDGEiQ", "left_nav", "42px/900"),
    ("system_title", "EDGEiQ PROFESSIONAL RACING INTELLIGENCE OPERATING SYSTEM", "topbar", "24px/900"),
    ("system_subtitle", "Information is not Intelligence. Evidence leads. Precision decides.", "topbar", "14px/400"),
    ("workspace_active", "FORM GUIDE", "left_nav + subnav", "13px/800"),
    ("breadcrumb", "MEETINGS > FLEMINGTON > RACE 1 > FORM GUIDE", "breadcrumb", "11px/900 uppercase"),
    ("race_title", "Race 1", "race_title", "26px/900"),
    ("race_name", "TAB Trophy", "race_title", "19px/900"),
    ("race_class", "BM 70", "race_title", "badge 14px/900"),
    ("summary_headers", "NO|SILK|HORSE|TRAINER|JOCKEY|BARRIER|WEIGHT (kg)|DAYS|EPI|EPI +/-|EARLY SPEED (Gate)|LATE SPEED (Finish)|SUITABILITY (Today)|FORM MOMENTUM (Last 5)|MARKET|EDGEiQ PRICE (Fair)|EDGE|FLUC 60s %", "summary_table", "10px/900 uppercase"),
    ("selected_horse", "JIMMYSSTAR", "runner_header", "22px/900"),
    ("metric_strip", "EPI (Today)|EPI Rank|Suitability|Form Momentum|Edge|EDGEiQ Price (Fair)|Market", "runner_header", "11px/900 uppercase"),
    ("today_match", "TODAY'S MATCH", "today_match", "12px/900 uppercase"),
    ("profile_matrix", "HORSE PROFILE (CAREER)", "profile_matrix", "12px/900 uppercase"),
    ("insights", "TODAY'S MATCH INSIGHTS", "match_insights", "12px/900 uppercase"),
    ("recent_form", "RECENT FORM (LAST 8 STARTS)", "recent_form", "12px/900 uppercase"),
]

STYLE = {
    "blue": "#0759d7",
    "blue_dark": "#07166c",
    "navy": "#091a44",
    "text": "#07135f",
    "muted": "#52637f",
    "line": "#dde5ef",
    "line_strong": "#c8d3df",
    "surface": "#ffffff",
    "surface_soft": "#f7f9fc",
    "blue_soft": "#edf4ff",
    "green": "#087e2f",
    "green_soft": "#eaf7ee",
    "red": "#cc3340",
    "red_soft": "#fdecec",
    "font_family": "Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
}

def read_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def main():
    measurement = read_json(MEASURE)
    legacy = read_json(LEGACY_MEASURE)
    canvas = measurement.get("canvas") or legacy.get("canvas") or {"width":1536,"height":1024}
    spec = {
        "version": "FORM_GUIDE_APPROVED_PIXEL_SPEC_V1",
        "authority": "05_FORM_GUIDE_APPROVED.png",
        "source_png_sha256": measurement.get("sha256"),
        "canvas": canvas,
        "implementation_scope": "Live React/CSS FORM GUIDE screen. Data remains governed/live; no demo data; no model maths changed.",
        "style_tokens": STYLE,
        "regions": REGIONS,
        "text_spec": [
            {"id": row[0], "text": row[1], "region": row[2], "typography": row[3]} for row in TEXT
        ],
        "legacy_machine_measurement": {
            "content_bounds": legacy.get("content_bounds"),
            "major_vertical_boundaries_x": legacy.get("major_vertical_boundaries_x", []),
            "major_horizontal_boundaries_y": legacy.get("major_horizontal_boundaries_y", []),
            "dominant_colors": legacy.get("dominant_colors", [])[:12],
        },
        "acceptance": {
            "required_live_regions": [r["id"] for r in REGIONS if r["id"] not in {"canvas"}],
            "required_columns": [c.strip() for c in TEXT[8][1].split("|")],
            "must_preserve": ["live governed field", "enriched form guide feed", "EPI/ERI/pricing/rating calculations"],
            "must_not_show": ["demo runner data", "approximation-only placeholder", "redesigned unrelated workspace"]
        }
    }
    JSON_OUT.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    with GEOM_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id","x","y","w","h","role","notes"])
        writer.writeheader(); writer.writerows(REGIONS)
    with TEXT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id","text","region","typography"])
        writer.writerows(TEXT)
    TOKENS_CSS.write_text(""":root {
  --fg-approved-blue: #0759d7;
  --fg-approved-blue-dark: #07166c;
  --fg-approved-navy: #091a44;
  --fg-approved-text: #07135f;
  --fg-approved-muted: #52637f;
  --fg-approved-line: #dde5ef;
  --fg-approved-line-strong: #c8d3df;
  --fg-approved-surface: #ffffff;
  --fg-approved-surface-soft: #f7f9fc;
  --fg-approved-blue-soft: #edf4ff;
  --fg-approved-green: #087e2f;
  --fg-approved-green-soft: #eaf7ee;
  --fg-approved-red: #cc3340;
  --fg-approved-red-soft: #fdecec;
  --fg-approved-font: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
""", encoding="utf-8")
    md = [
        "# FORM GUIDE APPROVED PIXEL SPEC V1",
        "",
        f"Source authority: `05_FORM_GUIDE_APPROVED.png`",
        f"SHA-256: `{measurement.get('sha256','')}`",
        f"Canvas: `{canvas.get('width')} x {canvas.get('height')}`",
        "",
        "This spec is the implementation contract for the live FORM GUIDE workspace. It preserves live governed data and limits changes to React structure, copy, interactions, and CSS presentation.",
        "",
        "## Major Regions",
        "",
        "| Region | x | y | w | h | Role |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in REGIONS:
        md.append(f"| `{r['id']}` | {r['x']} | {r['y']} | {r['w']} | {r['h']} | {r['role']} |")
    md += [
        "",
        "## Required Live Behaviour",
        "",
        "- FORM GUIDE opens inside the preserved EDGEiQ race workspace navigation.",
        "- Summary table shows every governed runner from the selected race.",
        "- Expanding a runner shows the selected horse profile, today's match, career matrix, insights, and recent form table.",
        "- The implementation must use live governed data only. Missing values render as a clean dash, not invented content.",
        "- EPI/ERI/pricing/probability/rating calculations are not modified by this spec.",
        "",
        "## Required Text System",
        "",
        "See `FORM_GUIDE_APPROVED_TEXT_SPEC_V1.csv` for exact visible labels and typography intent.",
        "",
        "## Required Geometry",
        "",
        "See `FORM_GUIDE_APPROVED_GEOMETRY_V1.csv` for region-level pixel boxes measured against the approved 1536x1024 PNG.",
    ]
    MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"status":"FORM_GUIDE_APPROVED_PIXEL_SPEC_BUILT", "files":[str(MD), str(JSON_OUT), str(TEXT_CSV), str(GEOM_CSV), str(TOKENS_CSS)]}, indent=2))

if __name__ == "__main__":
    main()
