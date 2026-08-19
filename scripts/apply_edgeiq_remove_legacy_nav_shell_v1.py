from pathlib import Path
from datetime import datetime, timezone
import csv
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRE_REMOVE_LEGACY_NAV_SHELL_V1_20260630.tsx"
SUMMARY = ROOT / "public" / "data" / "edgeiq_remove_legacy_nav_shell_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_remove_legacy_nav_shell_v1_report.txt"

LEGACY_TABS = ["OVERVIEW", "INTELLIGENCE", "MARKET", "TRACKING", "RESULTS"]
PRODUCT_TABS = ["RACE", "FIELD", "MAP", "INSIGHTS", "MARKET", "RESULTS"]


def write_summary(rows):
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def remove_block(text, start_marker, end_marker, label):
    start = text.find(start_marker)
    if start == -1:
        return text, False, f"{label}_START_NOT_FOUND"
    end = text.find(end_marker, start)
    if end == -1:
        return text, False, f"{label}_END_NOT_FOUND"
    end += len(end_marker)
    while end < len(text) and text[end] in "\r\n":
        end += 1
    return text[:start] + text[end:], True, f"{label}_REMOVED"


def contains_product_tabs(text):
    return all(f'label: "{label}"' in text for label in PRODUCT_TABS)


def main():
    if not TSX.exists():
        raise FileNotFoundError(TSX)

    original = TSX.read_text(encoding="utf-8")
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TSX, CHECKPOINT)

    before = original
    legacy_ticker_before = ("EDGEIQ RACING" in before.upper()) or ("TICKER" in before.upper())
    old_tab_sequence_before = "OVERVIEW" in before.upper() and "TRACKING" in before.upper()
    product_tabs_before = contains_product_tabs(before)

    text = before

    race_breadcrumb_marker = '      <nav style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 10,'
    text, breadcrumb_removed, breadcrumb_status = remove_block(text, race_breadcrumb_marker, "      </nav>", "RACE_BREADCRUMB_NAV")

    command_header_marker = '      <header className="edgeiq-command-header" style={headerStyle}>'
    text, command_header_removed, command_header_status = remove_block(text, command_header_marker, "      </header>", "LEGACY_RACE_HEADER")

    text = text.replace(
        '<section className="edgeiq-workspace-tabs" style={{ ...panelStyle, padding: 10 }}>',
        '<section className="edgeiq-workspace-tabs edgeiq-primary-product-tabs" style={{ ...panelStyle, padding: 10 }}>',
        1,
    )
    text = text.replace('<span>INTELLIGENCE WORKSPACES</span>', '<span>RACE PAGE</span>', 1)

    TSX.write_text(text, encoding="utf-8")

    after = text
    legacy_ticker_after = ("EDGEIQ RACING" in after.upper()) or ("TICKER" in after.upper())
    old_tabs_after = ("OVERVIEW" in after.upper()) or ("TRACKING" in after.upper())
    product_tabs_after = contains_product_tabs(after)
    legacy_command_header_after = 'className="edgeiq-command-header"' in after
    race_breadcrumb_after = race_breadcrumb_marker in after
    race_meta_count_after = after.count('className="edgeiq-intel-race-meta"')

    status = "LEGACY_NAV_SHELL_REMOVED" if command_header_removed and product_tabs_after and not old_tabs_after else "LEGACY_NAV_SHELL_REVIEW_REQUIRED"

    rows = [
        {"metric": "status", "value": status},
        {"metric": "checkpoint", "value": str(CHECKPOINT.relative_to(ROOT))},
        {"metric": "race_breadcrumb_removed", "value": "YES" if breadcrumb_removed else "NO"},
        {"metric": "race_breadcrumb_status", "value": breadcrumb_status},
        {"metric": "legacy_race_header_removed", "value": "YES" if command_header_removed else "NO"},
        {"metric": "legacy_race_header_status", "value": command_header_status},
        {"metric": "legacy_ticker_removed", "value": "YES" if not legacy_ticker_after else "NO"},
        {"metric": "legacy_ticker_was_present_before", "value": "YES" if legacy_ticker_before else "NO"},
        {"metric": "old_tabs_removed", "value": "YES" if not old_tabs_after else "NO"},
        {"metric": "old_tabs_were_present_before", "value": "YES" if old_tab_sequence_before else "NO"},
        {"metric": "new_tabs_retained", "value": "YES" if product_tabs_after else "NO"},
        {"metric": "new_tabs_present_before", "value": "YES" if product_tabs_before else "NO"},
        {"metric": "race_is_default", "value": "YES" if 'useState<IntelMode>("COMMAND")' in after else "NO"},
        {"metric": "command_header_remaining", "value": "YES" if legacy_command_header_after else "NO"},
        {"metric": "race_breadcrumb_remaining", "value": "YES" if race_breadcrumb_after else "NO"},
        {"metric": "race_meta_class_remaining_count", "value": str(race_meta_count_after)},
        {"metric": "ui_only", "value": "YES"},
        {"metric": "backend_data_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "completed_at", "value": datetime.now(timezone.utc).isoformat()},
    ]
    write_summary(rows)

    with REPORT.open("w", encoding="utf-8") as f:
        f.write("EDGEiQ Remove Legacy Nav Shell V1\n")
        f.write(f"Status: {status}\n\n")
        f.write("Changes applied:\n")
        f.write(f"- Checkpoint created: {CHECKPOINT.relative_to(ROOT)}\n")
        f.write(f"- Race breadcrumb/navigation block removed: {'YES' if breadcrumb_removed else 'NO'} ({breadcrumb_status})\n")
        f.write(f"- Legacy race header/metadata/top ticker surface removed: {'YES' if command_header_removed else 'NO'} ({command_header_status})\n")
        f.write("- Product tab section retained and promoted with edgeiq-primary-product-tabs class.\n")
        f.write("- Product tab title changed from INTELLIGENCE WORKSPACES to RACE PAGE.\n\n")
        f.write("Validation before build:\n")
        f.write(f"- Legacy ticker present after: {'YES' if legacy_ticker_after else 'NO'}\n")
        f.write(f"- Old tabs OVERVIEW/TRACKING present after: {'YES' if old_tabs_after else 'NO'}\n")
        f.write(f"- New tabs retained: {'YES' if product_tabs_after else 'NO'}\n")
        f.write(f"- RACE default retained: {'YES' if 'useState<IntelMode>(\"COMMAND\")' in after else 'NO'}\n\n")
        f.write("Safety confirmations:\n")
        f.write("- UI only: YES\n")
        f.write("- Backend data changed: NO\n")
        f.write("- Pricing changed: NO\n")
        f.write("- Probability changed: NO\n")
        f.write("- V6.1 changed: NO\n")
        f.write("- V7.2G2 changed: NO\n")

    print(status)


if __name__ == "__main__":
    main()
