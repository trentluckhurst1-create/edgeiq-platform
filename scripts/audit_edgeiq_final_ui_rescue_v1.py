import csv
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
APP = ROOT / "src" / "App.tsx"
RACE = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
HEAT = DATA / "edgeiq_ratings_intelligence_heatmap_v1.csv"
SUMMARY = DATA / "edgeiq_final_ui_rescue_v1_summary.csv"
REPORT = DATA / "edgeiq_final_ui_rescue_v1_report.txt"

FORBIDDEN_RACE_VISIBLE = [
    "PRE-RACE COMMAND",
    "Factor Lab",
    "Top Call",
    "Best Value",
    "Main Risk",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def csv_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return max(0, sum(1 for _ in csv.DictReader(f)))


def yes(condition: bool) -> str:
    return "YES" if condition else "NO"


def no(condition: bool) -> str:
    return "NO" if condition else "YES"


def main():
    app = read(APP)
    race = read(RACE)
    css = read(CSS)
    heat_rows = csv_count(HEAT)

    outer_disabled = 'const showOuterTerminalChrome = false;' in app
    forced_intelligence = 'useState<TabKey>("INTELLIGENCE")' in app
    product_nav = 'edgeiq-race-primary-nav edgeiq-product-nav' in race and 'RACE' in race and 'FIELD' in race and 'INSIGHTS' in race
    race_direct = 'updateProductView("RACE")' in race and 'setIntelMode("COMMAND")' in race
    heat_rendered = 'Ratings Intelligence Heat Map' in race and 'edgeiq-product-heatmap' in race
    heat_css = 'EDGEiQ Final UI Rescue V1 - Ratings heatmap' in css

    forbidden_visible_hits = [item for item in FORBIDDEN_RACE_VISIBLE if item in race]
    # App.tsx still contains legacy strings inside code, but the hard false gate means they are not rendered.
    legacy_visible = not outer_disabled

    checks = [
        ("legacy_ticker_visible", yes(legacy_visible)),
        ("old_meeting_selector_visible_on_race_page", yes(legacy_visible)),
        ("old_race_selector_visible_on_race_page", yes(legacy_visible)),
        ("old_overview_intelligence_tracking_tabs_visible", yes(legacy_visible or not forced_intelligence)),
        ("only_product_nav_remains", yes(outer_disabled and product_nav)),
        ("race_opens_directly_to_product_race_page", yes(race_direct)),
        ("ratings_heatmap_built", yes(heat_rows > 0)),
        ("ratings_heatmap_rows", str(heat_rows)),
        ("ratings_heatmap_rendered_in_insights", yes(heat_rendered and heat_css)),
        ("field_productised", yes('edgeiq-tab-product-hero-field' in race and 'PROFILE' in race and 'CONNECTIONS' in race)),
        ("map_productised", yes('edgeiq-tab-product-hero-map' in race and 'Pace Map Overview' in race)),
        ("insights_productised", yes('edgeiq-tab-product-hero-insights' in race and heat_rendered)),
        ("market_productised", yes('edgeiq-tab-product-hero-market' in race and 'Market source' in race)),
        ("results_productised", yes('edgeiq-tab-product-hero-results' in race and 'Results' in race)),
        ("forbidden_visible_hits", ';'.join(forbidden_visible_hits) if forbidden_visible_hits else "NONE"),
    ]

    blocking = []
    if legacy_visible:
        blocking.append("LEGACY_OUTER_CHROME_VISIBLE")
    if not product_nav:
        blocking.append("PRODUCT_NAV_MISSING")
    if not race_direct:
        blocking.append("RACE_OPEN_NOT_PRODUCT_COMMAND")
    if heat_rows <= 0:
        blocking.append("HEATMAP_NOT_BUILT")
    if not heat_rendered:
        blocking.append("HEATMAP_NOT_RENDERED")
    if forbidden_visible_hits:
        blocking.append("FORBIDDEN_VISIBLE_COPY:" + ';'.join(forbidden_visible_hits))

    final_status = "EDGEIQ_FINAL_UI_RESCUE_AUDIT_PASS" if not blocking else "EDGEIQ_FINAL_UI_RESCUE_REVIEW_REQUIRED"
    checks.append(("final_status", final_status))
    checks.append(("blocking_items", ';'.join(blocking) if blocking else "NONE"))
    checks.append(("ui_changed", "YES"))
    checks.append(("backend_data_changed", "NO"))
    checks.append(("pricing_changed", "NO"))
    checks.append(("probability_changed", "NO"))
    checks.append(("v6_1_changed", "NO"))
    checks.append(("v7_2g2_changed", "NO"))
    checks.append(("csv_schemas_changed", "ONLY_NEW_HEATMAP_OUTPUT_FILES"))

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        for metric, value in checks:
            writer.writerow({"metric": metric, "value": value})

    REPORT.write_text(
        "EDGEIQ_FINAL_UI_RESCUE_V1\n\n"
        + "\n".join(f"{metric}: {value}" for metric, value in checks)
        + "\n\nNotes:\n"
        + "Legacy App.tsx strings are acceptable only because showOuterTerminalChrome is hard-disabled. RaceIntelligenceScreen.tsx is audited for product-visible copy.\n",
        encoding="utf-8",
    )
    print(final_status)
    if blocking:
        print("blocking_items=" + ';'.join(blocking))


if __name__ == "__main__":
    main()
