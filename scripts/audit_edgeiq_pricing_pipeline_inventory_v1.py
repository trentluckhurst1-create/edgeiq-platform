import re
from pathlib import Path

from edgeiq_pricing_research_common import DATA, ROOT, read_csv, text, write_csv


OUT = DATA / "edgeiq_pricing_pipeline_inventory_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_pricing_pipeline_inventory_summary_v1.csv"

TERMS = re.compile(r"(price|probab|fair|rating|v6|v6_1|market|calibration)", re.I)
PRODUCTION_HINTS = re.compile(r"(live_runner_board|production|terminal_feed|execution_board|runner_board|fair_price_v6_1\.csv|probability_engine_v4_1\.csv)", re.I)
RESEARCH_HINTS = re.compile(r"(research|audit|candidate|replay|backtest|calibration|summary|diagnostic)", re.I)


def infer_purpose(name: str) -> str:
    lower = name.lower()
    if "live_runner_board" in lower:
        return "live board / production display feed"
    if "fair_price" in lower:
        return "fair price generation or audit"
    if "probability" in lower:
        return "probability generation or calibration"
    if "rating" in lower:
        return "rating input or rating audit"
    if "market" in lower:
        return "market price input or market audit"
    if "calibration" in lower:
        return "calibration audit"
    return "pricing-related file"


def parse_script(path: Path) -> dict[str, str]:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        source = ""
    inputs = sorted(set(re.findall(r'(?:DATA|ROOT)\s*/\s*"([^"]+\.csv)"', source)))
    outputs = sorted(set(re.findall(r'OUT\w*\s*=\s*DATA\s*/\s*"([^"]+)"', source)))
    columns = sorted(set(re.findall(r'"([^"]*(?:probability|fair_price|price|confidence|rating)[^"]*)"', source, re.I)))
    return {
        "inputs": "; ".join(inputs[:20]),
        "outputs": "; ".join(outputs[:20]),
        "probability_columns": "; ".join([c for c in columns if "prob" in c.lower()][:20]),
        "fair_price_columns": "; ".join([c for c in columns if "fair" in c.lower() or "price" in c.lower()][:20]),
        "confidence_columns": "; ".join([c for c in columns if "confidence" in c.lower()][:20]),
        "normalisation_logic_detected": "YES" if re.search(r"normalis|normaliz|sum\(.*prob|probability_sum|total_prob", source, re.I | re.S) else "NO",
        "multipliers_detected": "YES" if re.search(r"multiplier|\\*=", source, re.I) else "NO",
        "field_size_adjustment_detected": "YES" if re.search(r"field_size|_field_size", source, re.I) else "NO",
        "caps_floors_detected": "YES" if re.search(r"cap|floor|clip|clamp|min\(|max\(", source, re.I) else "NO",
    }


def parse_csv(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    fields = list(rows[0].keys()) if rows else []
    if not fields and path.exists():
        try:
            fields = path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()[0].split(",")
        except Exception:
            fields = []
    prob = [c for c in fields if "prob" in c.lower()]
    fair = [c for c in fields if "fair" in c.lower() or "price" in c.lower()]
    conf = [c for c in fields if "confidence" in c.lower()]
    return {
        "inputs": "",
        "outputs": path.name,
        "probability_columns": "; ".join(prob[:30]),
        "fair_price_columns": "; ".join(fair[:30]),
        "confidence_columns": "; ".join(conf[:30]),
        "normalisation_logic_detected": "YES" if any("normalis" in c.lower() or "normaliz" in c.lower() for c in fields) else "NO",
        "multipliers_detected": "YES" if any("multiplier" in c.lower() for c in fields) else "NO",
        "field_size_adjustment_detected": "YES" if any("field_size" in c.lower() for c in fields) else "NO",
        "caps_floors_detected": "YES" if any(("cap" in c.lower() or "floor" in c.lower()) for c in fields) else "NO",
    }


def main() -> None:
    rows: list[dict[str, object]] = []
    candidates = [p for p in (ROOT / "scripts").glob("*.py") if TERMS.search(p.name)]
    candidates += [p for p in DATA.glob("*.csv") if TERMS.search(p.name)]

    for path in sorted(candidates, key=lambda p: (p.suffix, p.name.lower())):
        meta = parse_script(path) if path.suffix.lower() == ".py" else parse_csv(path)
        name = path.name
        classification = "PRODUCTION" if PRODUCTION_HINTS.search(name) and not RESEARCH_HINTS.search(name) else "RESEARCH_OR_AUDIT"
        rows.append(
            {
                "script_or_file_name": name,
                "path": str(path.relative_to(ROOT)),
                "purpose_inferred": infer_purpose(name),
                "inputs": meta["inputs"],
                "outputs": meta["outputs"],
                "production_or_research": classification,
                "probability_columns": meta["probability_columns"],
                "fair_price_columns": meta["fair_price_columns"],
                "confidence_columns": meta["confidence_columns"],
                "normalisation_logic_detected": meta["normalisation_logic_detected"],
                "multipliers_detected": meta["multipliers_detected"],
                "field_size_adjustment_detected": meta["field_size_adjustment_detected"],
                "caps_floors_detected": meta["caps_floors_detected"],
                "safe_to_touch": "NO" if classification == "PRODUCTION" else "YES_RESEARCH_CLONE_ONLY",
            }
        )

    production_path = [
        {"metric": "current_production_path", "value": "edgeiq_live_runner_board_v1.csv columns projected_rating_V6_1_RESEARCH/total_rating_points -> win_pct or V6_1_RESEARCH_probability -> display_fair_price/ui_fair_price/fair_price -> live board"},
        {"metric": "inventory_rows", "value": len(rows)},
        {"metric": "production_like_rows", "value": sum(1 for row in rows if row["production_or_research"] == "PRODUCTION")},
        {"metric": "research_or_audit_rows", "value": sum(1 for row in rows if row["production_or_research"] != "PRODUCTION")},
        {"metric": "safe_to_touch_rule", "value": "NO for production; YES only for research clone outputs"},
    ]
    fields = [
        "script_or_file_name",
        "path",
        "purpose_inferred",
        "inputs",
        "outputs",
        "production_or_research",
        "probability_columns",
        "fair_price_columns",
        "confidence_columns",
        "normalisation_logic_detected",
        "multipliers_detected",
        "field_size_adjustment_detected",
        "caps_floors_detected",
        "safe_to_touch",
    ]
    write_csv(OUT, rows, fields)
    write_csv(OUT_SUMMARY, production_path, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
