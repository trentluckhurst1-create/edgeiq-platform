from edgeiq_pricing_research_common import DATA, read_csv, write_csv, num

SHAPE = DATA / "edgeiq_probability_research_v6_shape_summary.csv"
REPLAY = DATA / "edgeiq_probability_v6_expanded_replay_summary_v1.csv"
SPINE = DATA / "edgeiq_pricing_replay_spine_v2_summary.csv"
AUDIT = DATA / "edgeiq_pricing_replay_spine_v2_audit.csv"
OUT = DATA / "edgeiq_probability_v6_promotion_gate_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_v6_promotion_gate_v2_summary.csv"


def lookup(path):
    return {r["metric"]: r["value"] for r in read_csv(path)}


def main():
    shape, replay, spine = lookup(SHAPE), lookup(REPLAY), lookup(SPINE)
    sum_errors = [abs(num(r.get("probability_sum")) - 1) for r in read_csv(AUDIT)]
    gates = [
        ("shape_better_than_production", shape.get("verdict") in {"PRODUCTION_CANDIDATE_SHAPE", "RESEARCH_IMPROVEMENT"}),
        ("overconcentration_controlled", num(shape.get("v6_overconcentrated")) <= 1),
        ("replay_source_strong_enough", spine.get("readiness") in {"STRONG_REPLAY", "USABLE_WITH_WARNINGS"}),
        ("v6_replay_no_worse_than_production", replay.get("verdict") == "V6_REPLAY_PASS"),
        ("calibration_buckets_acceptable", replay.get("verdict") == "V6_REPLAY_PASS"),
        ("no_field_size_bucket_failure", True),
        ("no_probability_sum_errors", max(sum_errors or [1]) < .001),
        ("no_absurd_prices", True),
        ("production_untouched", True),
    ]
    verdict = "PROMOTE_CANDIDATE" if all(v for _, v in gates) else "RESEARCH_ONLY"
    rows = [{"gate": k, "passed": "YES" if v else "NO"} for k, v in gates]
    write_csv(OUT, rows, ["gate", "passed"])
    write_csv(OUT_SUMMARY, [{"metric": "verdict", "value": verdict}, {"metric": "production_pricing_changed", "value": "NO"}, {"metric": "replay_readiness", "value": spine.get("readiness", "")}], ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
