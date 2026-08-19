from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
DATA = ROOT / "public" / "data"

TSX_CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRE_FEATURE_PRODUCTISATION_V1_20260630.tsx"
CSS_CHECKPOINT = ROOT / "src" / "styles" / "edgeiqProductTerminalV1_CHECKPOINT_PRE_FEATURE_PRODUCTISATION_V1_20260630.css"
SUMMARY = DATA / "edgeiq_feature_productisation_v1_summary.csv"
REPORT = DATA / "edgeiq_feature_productisation_v1_report.txt"


def read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def checkpoint(source: Path, target: Path) -> bool:
    if target.exists():
        return target.stat().st_size > 0
    target.write_bytes(source.read_bytes())
    return target.exists() and target.stat().st_size == source.stat().st_size


def replace_once(text: str, old: str, new: str, changes: list[str], label: str) -> str:
    if old not in text:
        return text
    changes.append(label)
    return text.replace(old, new, 1)


def insert_after_regex(text: str, pattern: str, insertion: str, sentinel: str, changes: list[str], label: str) -> str:
    if sentinel in text:
        return text
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return text
    changes.append(label)
    return text[: match.end()] + insertion + text[match.end() :]


FIELD_HERO = '''

        <div className="edgeiq-tab-product-hero edgeiq-tab-product-hero-field">
          <div className="edgeiq-tab-product-mark" aria-hidden="true">&#9822;</div>
          <div className="edgeiq-tab-product-copy">
            <span>FIELD INTELLIGENCE</span>
            <strong>Runner profiles, current figures and form evidence.</strong>
            <em>Compact race-table analysis with selected-runner evidence ready below.</em>
          </div>
          <div className="edgeiq-tab-product-chip-row" aria-label="Field status">
            <span className="edgeiq-product-status-chip good">{activeRaceRows.length} Runners</span>
            <span className="edgeiq-product-status-chip info">{selected ? horse(selected.row) : "No runner selected"}</span>
            <span className="edgeiq-product-status-chip source">Profiles Active</span>
          </div>
        </div>
'''

MAP_HERO = '''

            <div className="edgeiq-tab-product-hero edgeiq-tab-product-hero-map">
              <div className="edgeiq-tab-product-mark" aria-hidden="true">&#9822;</div>
              <div className="edgeiq-tab-product-copy">
                <span>MAP INTELLIGENCE</span>
                <strong>Lane-based speed map with barrier-side context.</strong>
                <em>V3 relative speed drives lane position while race pressure and confidence frame the read.</em>
              </div>
              <div className="edgeiq-tab-product-chip-row" aria-label="Map status">
                <span className="edgeiq-product-status-chip good">{raceFieldSizeV2} Field</span>
                <span className="edgeiq-product-status-chip warn">Pressure {racePressureV2}</span>
                <span className="edgeiq-product-status-chip info">Confidence {mapConfidenceV2}</span>
              </div>
            </div>
'''

INSIGHTS_HERO = '''

        <div className="edgeiq-tab-product-hero edgeiq-tab-product-hero-insights">
          <div className="edgeiq-tab-product-mark" aria-hidden="true">&#9822;</div>
          <div className="edgeiq-tab-product-copy">
            <span>INSIGHT LAB</span>
            <strong>Evidence families, current read and why-it-matters context.</strong>
            <em>Focused analysis for the selected runner without exposing diagnostics.</em>
          </div>
          <div className="edgeiq-tab-product-chip-row" aria-label="Insights status">
            <span className="edgeiq-product-status-chip info">{selected ? horse(selected.row) : "Select runner"}</span>
            <span className="edgeiq-product-status-chip good">{selectedFactorDetailSections.length} Evidence Cards</span>
            <span className="edgeiq-product-status-chip source">Factor Lab</span>
          </div>
        </div>
'''

MARKET_HERO = '''

            <div className="edgeiq-tab-product-hero edgeiq-tab-product-hero-market">
              <div className="edgeiq-tab-product-mark" aria-hidden="true">&#9822;</div>
              <div className="edgeiq-tab-product-copy">
                <span>MARKET INTELLIGENCE</span>
                <strong>Source state, price context and alignment without recommendations.</strong>
                <em>Market rows remain evidence context only; pricing mathematics are untouched.</em>
              </div>
              <div className="edgeiq-tab-product-chip-row" aria-label="Market status">
                <span className={marketConnected ? "edgeiq-product-status-chip good" : "edgeiq-product-status-chip warn"}>{marketConnected ? "Market Connected" : "Market Unavailable"}</span>
                <span className="edgeiq-product-status-chip info">{livePriceRowCount}/{activeRaceRows.length} Market Rows</span>
                <span className="edgeiq-product-status-chip source">{displayEdgeiqPriceCount}/{displayEvidenceFieldSize} EDGEiQ Prices</span>
              </div>
            </div>
'''

RESULTS_HERO = '''

          <div className="edgeiq-tab-product-hero edgeiq-tab-product-hero-results">
            <div className="edgeiq-tab-product-mark" aria-hidden="true">&#9822;</div>
            <div className="edgeiq-tab-product-copy">
              <span>RESULTS REVIEW</span>
              <strong>Official result capture and post-race intelligence separation.</strong>
              <em>Pre-race evidence remains separate until verified result data is available.</em>
            </div>
            <div className="edgeiq-tab-product-chip-row" aria-label="Results status">
              <span className="edgeiq-product-status-chip warn">Pending Official Result</span>
              <span className="edgeiq-product-status-chip info">{activeRaceRows.length} Race Runners</span>
              <span className="edgeiq-product-status-chip source">Review Locked</span>
            </div>
          </div>
'''

CSS_BLOCK = r'''

/* EDGEiQ Feature Productisation V1 */
.edgeiq-product-race .edgeiq-tab-product-hero {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr) minmax(280px, auto);
  gap: 16px;
  align-items: center;
  margin: 0 0 16px;
  padding: 16px;
  border: 1px solid rgba(42,245,220,.24);
  border-radius: 18px;
  background:
    radial-gradient(circle at 0% 0%, rgba(42,245,220,.16), transparent 18rem),
    radial-gradient(circle at 80% 20%, rgba(157,124,255,.12), transparent 24rem),
    linear-gradient(135deg, rgba(8,24,42,.92), rgba(3,10,22,.82));
  box-shadow: 0 18px 44px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.055);
  overflow: hidden;
}

.edgeiq-product-race .edgeiq-tab-product-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(90deg, rgba(42,245,220,.10), transparent 35%, rgba(245,196,81,.07));
  opacity: .92;
}

.edgeiq-product-race .edgeiq-tab-product-hero-field { border-color: rgba(49,145,255,.30); }
.edgeiq-product-race .edgeiq-tab-product-hero-map { border-color: rgba(42,245,220,.30); }
.edgeiq-product-race .edgeiq-tab-product-hero-insights { border-color: rgba(157,124,255,.30); }
.edgeiq-product-race .edgeiq-tab-product-hero-market { border-color: rgba(245,196,81,.30); }
.edgeiq-product-race .edgeiq-tab-product-hero-results { border-color: rgba(245,158,11,.30); }

.edgeiq-product-race .edgeiq-tab-product-mark {
  position: relative;
  z-index: 1;
  width: 58px;
  height: 58px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(42,245,220,.34);
  background:
    radial-gradient(circle at 35% 20%, rgba(42,245,220,.28), transparent 3.2rem),
    linear-gradient(145deg, rgba(8,30,48,.96), rgba(3,10,22,.92));
  color: #2af5dc;
  font-size: 31px;
  font-weight: 1000;
  box-shadow: 0 0 24px rgba(42,245,220,.12), inset 0 1px 0 rgba(255,255,255,.06);
}

.edgeiq-product-race .edgeiq-tab-product-copy {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 4px;
}

.edgeiq-product-race .edgeiq-tab-product-copy span {
  color: #2af5dc;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .24em;
  text-transform: uppercase;
}

.edgeiq-product-race .edgeiq-tab-product-copy strong {
  color: #ffffff;
  font-size: 19px;
  font-weight: 1000;
  line-height: 1.16;
}

.edgeiq-product-race .edgeiq-tab-product-copy em {
  color: #a9b8ca;
  font-size: 12px;
  font-style: normal;
  line-height: 1.4;
}

.edgeiq-product-race .edgeiq-tab-product-chip-row {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.edgeiq-product-race .edgeiq-product-status-chip {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(80,120,180,.28);
  background: rgba(5,12,22,.72);
  color: #dbeafe;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .08em;
  text-transform: uppercase;
  white-space: nowrap;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.045);
}

.edgeiq-product-race .edgeiq-product-status-chip.good {
  border-color: rgba(52,211,153,.38);
  color: #bbf7d0;
  background: rgba(6,78,59,.22);
}

.edgeiq-product-race .edgeiq-product-status-chip.warn {
  border-color: rgba(245,196,81,.38);
  color: #fde68a;
  background: rgba(113,63,18,.20);
}

.edgeiq-product-race .edgeiq-product-status-chip.info {
  border-color: rgba(125,211,252,.38);
  color: #bae6fd;
  background: rgba(12,74,110,.18);
}

.edgeiq-product-race .edgeiq-product-status-chip.source {
  border-color: rgba(157,124,255,.38);
  color: #ddd6fe;
  background: rgba(76,29,149,.18);
}

.edgeiq-product-race .edgeiq-product-mini-card,
.edgeiq-product-race .edgeiq-product-feature-panel,
.edgeiq-product-race .edgeiq-insight-factor-card {
  position: relative;
  z-index: 1;
  box-shadow: 0 14px 30px rgba(0,0,0,.20), inset 0 1px 0 rgba(255,255,255,.04);
}

.edgeiq-product-race .edgeiq-product-mini-card::before,
.edgeiq-product-race .edgeiq-product-feature-panel::before,
.edgeiq-product-race .edgeiq-insight-factor-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(42,245,220,.72), rgba(157,124,255,.18));
  opacity: .75;
  pointer-events: none;
}

.edgeiq-product-race .edgeiq-market-workspace .edgeiq-product-card:nth-child(1) { border-color: rgba(42,245,220,.34); }
.edgeiq-product-race .edgeiq-market-workspace .edgeiq-product-card:nth-child(2) { border-color: rgba(245,196,81,.34); }
.edgeiq-product-race .edgeiq-market-workspace .edgeiq-product-card:nth-child(3) { border-color: rgba(157,124,255,.34); }

.edgeiq-product-race .edgeiq-results-workspace .edgeiq-product-card {
  min-height: 150px;
}

@media (max-width: 1050px) {
  .edgeiq-product-race .edgeiq-tab-product-hero {
    grid-template-columns: 64px minmax(0, 1fr);
  }
  .edgeiq-product-race .edgeiq-tab-product-chip-row {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}

@media (max-width: 680px) {
  .edgeiq-product-race .edgeiq-tab-product-hero {
    grid-template-columns: 1fr;
  }
  .edgeiq-product-race .edgeiq-tab-product-mark {
    width: 52px;
    height: 52px;
  }
}
'''


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tsx_checkpoint_ok = checkpoint(TSX, TSX_CHECKPOINT)
    css_checkpoint_ok = checkpoint(CSS, CSS_CHECKPOINT)

    tsx = read_text(TSX)
    css = read_text(CSS)
    tsx_changes: list[str] = []
    css_changes: list[str] = []

    tsx = insert_after_regex(
        tsx,
        r'        <div style=\{titleStyle\}>\s*<span>FIELD</span>\s*<em>Runner list, profile evidence and current race context</em>\s*</div>',
        FIELD_HERO,
        "FIELD INTELLIGENCE",
        tsx_changes,
        "FIELD product hero inserted",
    )
    tsx = insert_after_regex(
        tsx,
        r'            <div style=\{titleStyle\}>\s*<span>Speed Map</span>\s*<em>\{raceShapeSummaryV2\}</em>\s*</div>',
        MAP_HERO,
        "MAP INTELLIGENCE",
        tsx_changes,
        "MAP product hero inserted",
    )
    tsx = insert_after_regex(
        tsx,
        r'        <div style=\{titleStyle\}>\s*<span>INSIGHTS</span>\s*<em>\{selected \? horse\(selected\.row\) : "No runner selected"\}</em>\s*</div>',
        INSIGHTS_HERO,
        "INSIGHT LAB",
        tsx_changes,
        "INSIGHTS product hero inserted",
    )
    tsx = insert_after_regex(
        tsx,
        r'            <div className="edgeiq-product-section-title">\s*<span>MARKET</span>\s*<em>Market/source state, fair-price context and timestamp-aware availability</em>\s*</div>',
        MARKET_HERO,
        "MARKET INTELLIGENCE",
        tsx_changes,
        "MARKET product hero inserted",
    )
    tsx = insert_after_regex(
        tsx,
        r'          <div className="edgeiq-product-section-title">\s*<span>RESULTS</span>\s*<em>Official result and post-race review</em>\s*</div>',
        RESULTS_HERO,
        "RESULTS REVIEW",
        tsx_changes,
        "RESULTS product hero inserted",
    )

    class_insertions = [
        (
            '<div key={`map-v2-summary-${card.label}`} style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 8, padding: 9, background: "rgba(5,12,22,.78)" }}>',
            '<div key={`map-v2-summary-${card.label}`} className="edgeiq-product-mini-card" style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 8, padding: 9, background: "rgba(5,12,22,.78)" }}>',
            "MAP summary mini-card class added",
        ),
        (
            '<section style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 10, padding: 11, background: "rgba(8,15,28,.80)" }}>',
            '<section className="edgeiq-product-feature-panel" style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 10, padding: 11, background: "rgba(8,15,28,.80)" }}>',
            "MAP feature panel class added",
        ),
        (
            '<section key={`selected-factor-detail-${section.title}`} style={factorDetailCardStyle}>',
            '<section key={`selected-factor-detail-${section.title}`} className="edgeiq-product-feature-panel edgeiq-insight-factor-card" style={factorDetailCardStyle}>',
            "INSIGHTS factor-card class added",
        ),
    ]
    for old, new, label in class_insertions:
        tsx = replace_once(tsx, old, new, tsx_changes, label)

    if "EDGEiQ Feature Productisation V1" not in css:
        css = css.rstrip() + CSS_BLOCK + "\n"
        css_changes.append("Feature productisation CSS appended")

    write_text(TSX, tsx)
    write_text(CSS, css)

    final_tsx = read_text(TSX)
    final_css = read_text(CSS)
    checks = {
        "field_hero": "FIELD INTELLIGENCE" in final_tsx,
        "map_hero": "MAP INTELLIGENCE" in final_tsx,
        "insights_hero": "INSIGHT LAB" in final_tsx,
        "market_hero": "MARKET INTELLIGENCE" in final_tsx,
        "results_hero": "RESULTS REVIEW" in final_tsx,
        "status_chips": "edgeiq-product-status-chip" in final_tsx and "edgeiq-product-status-chip" in final_css,
        "horse_iconography": "edgeiq-tab-product-mark" in final_tsx and "\\265E" in final_css,
        "product_css": "EDGEiQ Feature Productisation V1" in final_css,
        "primary_nav_unchanged": "edgeiq-race-primary-nav edgeiq-product-nav" in final_tsx,
    }

    rows = [
        ["metric", "value"],
        ["status", "EDGEIQ_FEATURE_PRODUCTISATION_V1_APPLIED"],
        ["tsx_checkpoint_created", "YES" if tsx_checkpoint_ok else "NO"],
        ["css_checkpoint_created", "YES" if css_checkpoint_ok else "NO"],
        ["tsx_changes", str(len(tsx_changes))],
        ["css_changes", str(len(css_changes))],
        ["new_navigation", "NO"],
        ["new_shell", "NO"],
        ["architecture_restructure", "NO"],
        ["pricing_changed", "NO"],
        ["probability_changed", "NO"],
        ["v6_1_changed", "NO"],
        ["v7_2g2_changed", "NO"],
        ["backend_data_changed", "NO"],
        ["csv_schema_changed", "NO"],
    ]
    for key, ok in checks.items():
        rows.append([key, "YES" if ok else "NO"])

    with SUMMARY.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    report_lines = [
        "EDGEiQ Feature Productisation V1",
        "Status: EDGEIQ_FEATURE_PRODUCTISATION_V1_APPLIED",
        "",
        "Scope:",
        "- Content productisation only for FIELD, MAP, INSIGHTS, MARKET and RESULTS.",
        "- Architecture frozen: no new navigation, no new shell, no routing restructure.",
        "- UI only; no backend, pricing, probability, V6.1, V7.2G2 or CSV schema changes.",
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
        "Verification:",
        *[f"- {key}: {'YES' if ok else 'NO'}" for key, ok in checks.items()],
    ]
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("EDGEIQ_FEATURE_PRODUCTISATION_V1_APPLIED")
    print(f"TSX checkpoint: {TSX_CHECKPOINT}")
    print(f"CSS checkpoint: {CSS_CHECKPOINT}")
    print(f"TSX changes: {len(tsx_changes)}")
    print(f"CSS changes: {len(css_changes)}")


if __name__ == "__main__":
    main()
