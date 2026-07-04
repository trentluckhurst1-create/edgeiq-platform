import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
MODULE_SUMMARIES = [
    ("EDGEIQ_WEIGHT_CHANGE_ENGINE_V1", DATA / "edgeiq_weight_change_engine_v1_summary.csv"),
    ("EDGEIQ_WEIGHT_DISTANCE_INTERACTION_V1", DATA / "edgeiq_weight_distance_interaction_v1_summary.csv"),
    ("EDGEIQ_WEIGHT_CONDITION_INTERACTION_V1", DATA / "edgeiq_weight_condition_interaction_v1_summary.csv"),
    ("EDGEIQ_WEIGHT_RUNSTYLE_INTERACTION_V1", DATA / "edgeiq_weight_runstyle_interaction_v1_summary.csv"),
]
OUT = DATA / "edgeiq_interaction_signal_comparison_v1.csv"
SUMMARY = DATA / "edgeiq_interaction_signal_comparison_v1_summary.csv"
REPORT = DATA / "edgeiq_interaction_signal_comparison_v1_report.txt"


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    fields = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def num(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    comparison = []
    band_rows = []
    missing = []
    for module, path in MODULE_SUMMARIES:
        if not path.exists():
            missing.append(str(path))
            continue
        rows = read_rows(path)
        overall = next((row for row in rows if row.get("context_band") == "OVERALL"), rows[0] if rows else {})
        if overall:
            out = dict(overall)
            out["comparison_scope"] = "OVERALL_MODULE_RESULT"
            out["built_at"] = built_at
            comparison.append(out)
        for row in rows:
            br = dict(row)
            br["comparison_scope"] = "MODULE_CONTEXT_BAND_RESULT"
            br["built_at"] = built_at
            band_rows.append(br)
    comparison.sort(key=lambda row: (num(row.get("top1_delta_pct")), num(row.get("top3_delta_pct"))), reverse=True)
    for idx, row in enumerate(comparison, start=1):
        row["research_rank_by_top1_then_top3"] = idx
    write_csv(OUT, comparison + band_rows)
    if comparison:
        best = comparison[0]
        promising = [row for row in comparison if row.get("verdict") == "PROMISING_RESEARCH_SIGNAL"]
        negative = [row for row in comparison if row.get("verdict") == "NEGATIVE_RESEARCH_SIGNAL"]
        summary_rows = [{
            "modules_compared": len(comparison),
            "missing_module_summaries": len(missing),
            "best_module": best.get("module"),
            "best_top1_delta_pct": best.get("top1_delta_pct"),
            "best_top3_delta_pct": best.get("top3_delta_pct"),
            "best_verdict": best.get("verdict"),
            "promising_modules": len(promising),
            "negative_modules": len(negative),
            "overall_research_verdict": "FURTHER_RESEARCH_ON_BEST_MODULE" if promising else "NO_PROMISING_STANDALONE_INTERACTION_YET",
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "ui_changed": "NO",
            "wfa_claim_made": "NO",
            "age_fields_used": "NO",
            "sex_fields_used": "NO",
            "built_at": built_at,
        }]
    else:
        summary_rows = [{
            "modules_compared": 0,
            "missing_module_summaries": len(missing),
            "overall_research_verdict": "INSUFFICIENT_SAMPLE",
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "ui_changed": "NO",
            "wfa_claim_made": "NO",
            "age_fields_used": "NO",
            "sex_fields_used": "NO",
            "built_at": built_at,
        }]
    write_csv(SUMMARY, summary_rows)
    lines = [
        "EDGEIQ_INTERACTION_SIGNAL_COMPARISON_V1",
        f"modules_compared={summary_rows[0].get('modules_compared')}",
        f"missing_module_summaries={summary_rows[0].get('missing_module_summaries')}",
        f"overall_research_verdict={summary_rows[0].get('overall_research_verdict')}",
        "production_changed=NO",
        "pricing_changed=NO",
        "v6_1_changed=NO",
        "v7_2g2_changed=NO",
        "ui_changed=NO",
        "wfa_claim_made=NO",
        "age_fields_used=NO",
        "sex_fields_used=NO",
        "",
        "OVERALL_MODULE_RESULTS",
    ]
    for row in comparison:
        lines.append(f"{row.get('research_rank_by_top1_then_top3')}. {row.get('module')}: races={row.get('races_tested')} runners={row.get('runners_tested')} top1_delta={row.get('top1_delta_pct')} top3_delta={row.get('top3_delta_pct')} adjusted_top1={row.get('adjusted_top1_win_pct')} adjusted_top3={row.get('adjusted_top3_win_pct')} verdict={row.get('verdict')}")
    if missing:
        lines.extend(["", "MISSING_MODULE_SUMMARIES"] + missing)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
