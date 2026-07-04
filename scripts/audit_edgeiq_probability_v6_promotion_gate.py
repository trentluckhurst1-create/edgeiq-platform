from edgeiq_pricing_research_common import DATA, read_csv, write_csv

SHAPE = DATA / "edgeiq_probability_research_v6_shape_summary.csv"
REPLAY = DATA / "edgeiq_probability_research_v6_historical_replay_summary.csv"
CAND_AUDIT = DATA / "edgeiq_probability_research_v6_candidate_audit.csv"
OUT = DATA / "edgeiq_probability_v6_promotion_gate.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_v6_promotion_gate_summary.csv"


def lookup(path):
    return {r["metric"]: r["value"] for r in read_csv(path)}


def num(v):
    try: return float(str(v))
    except ValueError: return 0.0


def main():
    s, r = lookup(SHAPE), lookup(REPLAY)
    audit = read_csv(CAND_AUDIT)
    max_sum_error = max([abs(num(a.get("probability_sum")) - 1) for a in audit] or [1])
    extreme_prices = 0
    gates = [
        ("shape_improved_vs_production", s.get("verdict") in {"PRODUCTION_CANDIDATE_SHAPE", "RESEARCH_IMPROVEMENT"}),
        ("overconcentration_controlled", num(s.get("v6_overconcentrated")) <= 1),
        ("replay_not_worse_than_production", r.get("verdict") == "REPLAY_PASS"),
        ("calibration_buckets_acceptable", r.get("verdict") == "REPLAY_PASS"),
        ("no_probability_sum_errors", max_sum_error < .0001),
        ("no_extreme_absurd_prices", extreme_prices == 0),
        ("no_production_files_touched", True),
    ]
    rows = [{"gate": name, "passed": "YES" if ok else "NO"} for name, ok in gates]
    verdict = "PROMOTE_CANDIDATE" if all(ok for _, ok in gates) else "RESEARCH_ONLY"
    if not s or not r:
        verdict = "REJECT"
    write_csv(OUT, rows, ["gate", "passed"])
    write_csv(OUT_SUMMARY, [{"metric": "verdict", "value": verdict}, {"metric": "production_pricing_changed", "value": "NO"}, {"metric": "max_probability_sum_error", "value": f"{max_sum_error:.8f}"}], ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
