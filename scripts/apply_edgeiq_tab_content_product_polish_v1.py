from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
DATA = ROOT / "public" / "data"

TSX_CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRE_TAB_CONTENT_PRODUCT_POLISH_V1_20260630.tsx"
CSS_CHECKPOINT = ROOT / "src" / "styles" / "edgeiqProductTerminalV1_CHECKPOINT_PRE_TAB_CONTENT_PRODUCT_POLISH_V1_20260630.css"
SUMMARY = DATA / "edgeiq_tab_content_product_polish_v1_summary.csv"
REPORT = DATA / "edgeiq_tab_content_product_polish_v1_report.txt"


def read_text_preserve(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def write_text_preserve(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def copy_checkpoint(source: Path, checkpoint: Path) -> bool:
    if checkpoint.exists():
        return checkpoint.stat().st_size > 0
    checkpoint.write_bytes(source.read_bytes())
    return checkpoint.exists() and checkpoint.stat().st_size == source.stat().st_size


def replace_once(text: str, old: str, new: str, changes: list[str]) -> str:
    if old in text:
        text = text.replace(old, new, 1)
        changes.append(old)
    return text


def replace_all(text: str, old: str, new: str, changes: list[str]) -> str:
    count = text.count(old)
    if count:
        text = text.replace(old, new)
        changes.append(f"{old} ({count})")
    return text


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    tsx_checkpoint_ok = copy_checkpoint(TSX, TSX_CHECKPOINT)
    css_checkpoint_ok = copy_checkpoint(CSS, CSS_CHECKPOINT)

    tsx = read_text_preserve(TSX)
    css = read_text_preserve(CSS)

    tsx_changes: list[str] = []
    css_changes: list[str] = []

    replacements = [
        ("Selected Runner Dossier", "Runner Profile"),
        (
            "Price, model, speed, suitability and connection evidence for the selected runner.",
            "Ratings, form, map position, setup and evidence for this runner.",
        ),
        ("EDGEiQ Decision Engine", "Model Explainability"),
        ("Why Ranked Here", "Evidence Profile"),
        ("Numeric supports, risks and factor snapshot", "Strengths, watchpoints and factor snapshot"),
        ("DNA Positives", "Profile Strengths"),
        ("DNA Risks", "Profile Watchpoints"),
        ("Main risk:", "Primary watchpoint:"),
        ("Selected Runner Map Card", "Runner Map Profile"),
        ("Historical Run Intelligence", "Historical Run Detail"),
    ]
    for old, new in replacements:
        tsx = replace_all(tsx, old, new, tsx_changes)

    # Keep internal mode names untouched, but show customer-facing tab copy.
    tsx = replace_once(
        tsx,
        "                {mode}\r\n              </button>",
        "                {mode === \"EXPLAINABILITY\" ? \"EVIDENCE\" : mode}\r\n              </button>",
        tsx_changes,
    )
    tsx = replace_once(
        tsx,
        "                {mode}\n              </button>",
        "                {mode === \"EXPLAINABILITY\" ? \"EVIDENCE\" : mode}\n              </button>",
        tsx_changes,
    )

    # Add lightweight product hooks to existing sections. These do not alter logic/routing.
    tsx = replace_once(
        tsx,
        'className="edgeiq-field-workspace edgeiq-product-section"',
        'className="edgeiq-field-workspace edgeiq-product-section edgeiq-product-workspace-premium"',
        tsx_changes,
    )
    tsx = replace_once(
        tsx,
        'className="edgeiq-map-workspace edgeiq-product-section"',
        'className="edgeiq-map-workspace edgeiq-product-section edgeiq-product-workspace-premium"',
        tsx_changes,
    )
    tsx = replace_once(
        tsx,
        'className="edgeiq-insights-workspace edgeiq-product-section"',
        'className="edgeiq-insights-workspace edgeiq-product-section edgeiq-product-workspace-premium"',
        tsx_changes,
    )
    tsx = replace_once(
        tsx,
        'className="edgeiq-market-workspace edgeiq-product-section"',
        'className="edgeiq-market-workspace edgeiq-product-section edgeiq-product-workspace-premium"',
        tsx_changes,
    )
    tsx = replace_once(
        tsx,
        'className="edgeiq-results-workspace edgeiq-product-section"',
        'className="edgeiq-results-workspace edgeiq-product-section edgeiq-product-workspace-premium"',
        tsx_changes,
    )

    # Remove a legacy diagnostic CSS selector block that referenced old betting-copy labels.
    legacy_css_pattern = re.compile(
        r'\.edgeiq-product-race \[style\*="OVERBET"\],\s*'
        r'\.edgeiq-product-race \[style\*="Best Value"\],\s*'
        r'\.edgeiq-product-race \[style\*="Top Call"\]\s*\{\s*'
        r'outline:\s*1px solid rgba\(245,196,81,\.18\);\s*'
        r'\}\s*',
        re.MULTILINE,
    )
    css, legacy_css_removed = legacy_css_pattern.subn("", css)
    if legacy_css_removed:
        css_changes.append("removed old Top Call / Best Value diagnostic CSS block")

    polish_css = r'''

/* EDGEiQ Tab Content Product Polish V1 */
.edgeiq-product-race .edgeiq-product-workspace-premium,
.edgeiq-product-race .edgeiq-race-premium-workspace {
  position: relative;
  overflow: hidden;
  border-color: rgba(42,245,220,.24) !important;
  background:
    radial-gradient(circle at 0% 0%, rgba(42,245,220,.105), transparent 24rem),
    radial-gradient(circle at 88% 8%, rgba(157,124,255,.095), transparent 28rem),
    linear-gradient(180deg, rgba(7,18,34,.93), rgba(3,10,22,.86)) !important;
  box-shadow:
    0 22px 54px rgba(0,0,0,.30),
    inset 0 1px 0 rgba(255,255,255,.045);
}

.edgeiq-product-race .edgeiq-product-workspace-premium::before,
.edgeiq-product-race .edgeiq-race-premium-workspace::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, #2af5dc, #3191ff, #9d7cff, #f5c451, #f59e0b);
  opacity: .75;
  pointer-events: none;
}

.edgeiq-product-race .edgeiq-product-workspace-premium::after {
  content: "\265E";
  position: absolute;
  right: 22px;
  top: 12px;
  color: rgba(42,245,220,.045);
  font-size: 92px;
  line-height: 1;
  font-weight: 900;
  pointer-events: none;
}

.edgeiq-product-race .edgeiq-product-section-title,
.edgeiq-product-race .edgeiq-field-workspace > div:first-child,
.edgeiq-product-race .edgeiq-map-workspace > div:first-child,
.edgeiq-product-race .edgeiq-insights-workspace > div:first-child {
  position: relative;
  z-index: 1;
}

.edgeiq-product-race .edgeiq-product-card,
.edgeiq-product-race .edgeiq-race-intel-card,
.edgeiq-product-race .edgeiq-race-factor-card,
.edgeiq-product-race .edgeiq-race-pace-card,
.edgeiq-product-race .edgeiq-race-watch-card {
  box-shadow: 0 16px 34px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.045);
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease;
}

.edgeiq-product-race .edgeiq-product-card:hover,
.edgeiq-product-race .edgeiq-race-intel-card:hover,
.edgeiq-product-race .edgeiq-race-factor-card:hover,
.edgeiq-product-race .edgeiq-race-pace-card:hover,
.edgeiq-product-race .edgeiq-race-watch-card:hover {
  transform: translateY(-1px);
  border-color: rgba(42,245,220,.38);
  box-shadow: 0 20px 44px rgba(0,0,0,.30), 0 0 26px rgba(42,245,220,.08), inset 0 1px 0 rgba(255,255,255,.06);
}

.edgeiq-product-race .edgeiq-field-workspace button,
.edgeiq-product-race .edgeiq-map-workspace button {
  transition: transform .16s ease, border-color .16s ease, box-shadow .16s ease, background .16s ease;
}

.edgeiq-product-race .edgeiq-field-workspace button:hover,
.edgeiq-product-race .edgeiq-map-workspace button:hover {
  transform: translateY(-1px);
  border-color: rgba(42,245,220,.34) !important;
  box-shadow: 0 10px 24px rgba(0,0,0,.24), 0 0 18px rgba(42,245,220,.08) !important;
}

.edgeiq-product-race .edgeiq-race-primary-nav button {
  position: relative;
  overflow: hidden;
}

.edgeiq-product-race .edgeiq-race-primary-nav button::after {
  content: "";
  position: absolute;
  left: 16%;
  right: 16%;
  bottom: 5px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(42,245,220,.0), rgba(42,245,220,.7), rgba(245,196,81,.0));
  opacity: .38;
}

.edgeiq-product-race .edgeiq-product-table-row {
  background:
    linear-gradient(90deg, rgba(42,245,220,.045), transparent 32%),
    rgba(5,12,22,.70);
}

.edgeiq-product-race .edgeiq-product-empty {
  background:
    radial-gradient(circle at 0% 0%, rgba(245,196,81,.12), transparent 14rem),
    rgba(245,158,11,.08);
}

@media (max-width: 760px) {
  .edgeiq-product-race .edgeiq-product-workspace-premium::after {
    display: none;
  }
}
'''

    if "EDGEiQ Tab Content Product Polish V1" not in css:
        css = css.rstrip() + polish_css + "\n"
        css_changes.append("appended shared premium tab-content styling")

    write_text_preserve(TSX, tsx)
    write_text_preserve(CSS, css)

    final_tsx = read_text_preserve(TSX)
    final_css = read_text_preserve(CSS)

    legacy_terms = {
        "old_ticker_literal_EDGEIQ_RACING": "EDGEIQ RACING" in final_tsx,
        "old_tab_overview_literal": "OVERVIEW" in final_tsx,
        "selected_runner_dossier": "Selected Runner Dossier" in final_tsx,
        "edgeiq_decision_engine": "EDGEiQ Decision Engine" in final_tsx,
        "why_ranked_here": "Why Ranked Here" in final_tsx,
        "dna_positives": "DNA Positives" in final_tsx,
        "dna_risks": "DNA Risks" in final_tsx,
        "top_call": "Top Call" in final_tsx or "Top Call" in final_css,
        "best_value": "Best Value" in final_tsx or "Best Value" in final_css,
    }

    rows = [
        ["metric", "value"],
        ["status", "EDGEIQ_TAB_CONTENT_PRODUCT_POLISH_APPLIED"],
        ["tsx_checkpoint_created", "YES" if tsx_checkpoint_ok else "NO"],
        ["css_checkpoint_created", "YES" if css_checkpoint_ok else "NO"],
        ["tsx_changes", str(len(tsx_changes))],
        ["css_changes", str(len(css_changes))],
        ["product_nav_changed", "NO"],
        ["pricing_changed", "NO"],
        ["probability_changed", "NO"],
        ["v6_1_changed", "NO"],
        ["v7_2g2_changed", "NO"],
        ["backend_data_changed", "NO"],
        ["csv_schema_changed", "NO"],
    ]
    for key, present in legacy_terms.items():
        rows.append([key, "PRESENT" if present else "ABSENT"])

    with SUMMARY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    report_lines = [
        "EDGEiQ Tab Content Product Polish V1",
        "Status: EDGEIQ_TAB_CONTENT_PRODUCT_POLISH_APPLIED",
        "",
        "Scope:",
        "- UI-only product content polish.",
        "- No navigation architecture changes.",
        "- No backend data, pricing, probability, V6.1, V7.2G2, or CSV schema changes.",
        "",
        "Checkpoints:",
        f"- {TSX_CHECKPOINT}",
        f"- {CSS_CHECKPOINT}",
        "",
        "TSX changes:",
        *[f"- {item}" for item in tsx_changes],
        "",
        "CSS changes:",
        *[f"- {item}" for item in css_changes],
        "",
        "Legacy/internal label audit:",
        *[f"- {key}: {'PRESENT' if present else 'ABSENT'}" for key, present in legacy_terms.items()],
        "",
        "Tabs productised:",
        "- RACE: retained premium race hero and intelligence cards.",
        "- FIELD: runner profile copy and evidence sub-tab language polished.",
        "- MAP: retained lane map and premium workspace treatment.",
        "- INSIGHTS: retained factor lab with product workspace styling.",
        "- MARKET: retained source-aware product cards/table.",
        "- RESULTS: retained clean product empty state.",
    ]
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("EDGEIQ_TAB_CONTENT_PRODUCT_POLISH_APPLIED")
    print(f"TSX checkpoint: {TSX_CHECKPOINT}")
    print(f"CSS checkpoint: {CSS_CHECKPOINT}")
    print(f"TSX changes: {len(tsx_changes)}")
    print(f"CSS changes: {len(css_changes)}")


if __name__ == "__main__":
    main()
