import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_intelligence_inventory_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_intelligence_inventory_v1_summary.csv"


ENGINES = [
    ("DNA", "edgeiq_runner_dna_v6_2.csv", "edgeiq_runner_dna_v6_2_summary.csv", "WIRED_RUNNER_DOSSIER", "runner board, V6.1 current fields, DNA factor profiles"),
    ("Campaign", "edgeiq_campaign_intelligence_engine_v1_1.csv", "", "WIRED_FACTOR_LAB", "runner history, prep stage profile"),
    ("Form", "edgeiq_form_intelligence_v2.csv", "edgeiq_form_intelligence_v2_summary.csv", "WIRED_FORM_TAB", "runner history detail, form history, race shape"),
    ("Performance Intelligence", "edgeiq_form_intelligence_v2.csv", "edgeiq_form_intelligence_v2_summary.csv", "WIRED_FORM_TAB", "form intelligence labels"),
    ("Connections", "edgeiq_connection_intelligence_v2_1.csv", "edgeiq_connection_intelligence_v2_1_quality_summary.csv", "WIRED_DOSSIER_AND_FACTOR_LAB", "trainer/jockey canonical bridge, historical profiles"),
    ("Surface Intelligence", "edgeiq_surface_intelligence_feed_v1.csv", "edgeiq_surface_intelligence_feed_v1_summary.csv", "BACKEND_ONLY", "true track rating profile, active race universe"),
    ("Track Bias", "edgeiq_track_bias_engine_v1.csv", "edgeiq_track_bias_engine_v1_summary.csv", "BACKEND_ONLY", "track/run-style/barrier bias profiles"),
    ("Chaos", "edgeiq_chaos_index_v1.csv", "edgeiq_chaos_index_v1_summary.csv", "WIRED_COMMAND_BAR_CHIP", "active race universe, pace uncertainty, market concentration"),
    ("Opportunity", "edgeiq_opportunity_score_v1.csv", "edgeiq_opportunity_score_v1_summary.csv", "WIRED_COMMAND_BAR_CHIP", "chaos, market disagreement, hidden performance, field size"),
    ("Market Research", "edgeiq_market_intelligence_v1.csv", "edgeiq_market_intelligence_v1_audit.csv", "PARTIAL_EXISTING_UI", "market feeds, market state"),
    ("Pricing Research", "edgeiq_probability_research_v5_2_guarded_temperature.csv", "edgeiq_probability_research_v5_2_shape_summary.csv", "RESEARCH_ONLY", "production probabilities, V5.1 temperature, V5.2 guardrails"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summary_value(path: str, keys: list[str]) -> str:
    rows = read_csv(DATA / path) if path else []
    lookup = {row.get("metric", ""): row.get("value", "") for row in rows}
    for key in keys:
        if key in lookup:
            return lookup[key]
    return ""


def readiness(engine: str, rows: int, summary: str) -> str:
    if rows <= 0:
        return "MISSING"
    if "READY_FOR_UI" in summary:
        return "READY_FOR_UI"
    if engine in {"Pricing Research", "Market Research"}:
        return "RESEARCH_ONLY"
    return "READY_RESEARCH"


def main() -> None:
    out = []
    for engine, feed, summary, ui_status, deps in ENGINES:
        rows = read_csv(DATA / feed)
        summary_text = "; ".join(f"{row.get('metric')}={row.get('value')}" for row in read_csv(DATA / summary)[:12]) if summary else ""
        coverage = len(rows)
        readiness_status = readiness(engine, coverage, summary_text)
        if engine == "Connections":
            coverage_note = f"{summary_value(summary, ['non_no_evidence_rows'])}/370 material evidence"
        elif engine == "Form":
            coverage_note = f"{summary_value(summary, ['form_rows_output'])}/370 output; {summary_value(summary, ['rows_with_history'])} direct history"
        elif engine in {"Chaos", "Opportunity", "Surface Intelligence", "Track Bias"}:
            coverage_note = f"{summary_value(summary, ['race_rows']) or coverage} race rows"
        elif engine == "Pricing Research":
            coverage_note = f"{summary_value(summary, ['race_rows']) or 25} race rows; research only"
        else:
            coverage_note = f"{coverage} rows"
        out.append({
            "engine": engine,
            "feed": feed,
            "coverage": coverage_note,
            "row_count": coverage,
            "readiness": readiness_status,
            "ui_status": ui_status,
            "dependencies": deps,
            "summary_reference": summary,
            "production_safe_to_modify": "NO",
            "research_safe_to_consume": "YES" if coverage else "NO",
        })
    write_csv(OUT, out, list(out[0].keys()))
    summary_rows = [
        {"metric": "engine_count", "value": len(out)},
        {"metric": "backend_only_or_research", "value": sum(1 for row in out if row["ui_status"] in {"BACKEND_ONLY", "RESEARCH_ONLY"})},
        {"metric": "wired_or_partial_ui", "value": sum(1 for row in out if row["ui_status"] not in {"BACKEND_ONLY", "RESEARCH_ONLY"})},
        {"metric": "missing_engines", "value": sum(1 for row in out if row["readiness"] == "MISSING")},
        {"metric": "production_changed", "value": "NO"},
    ]
    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
