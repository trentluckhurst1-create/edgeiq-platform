from collections import defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, clean, text, horse_key, race_key, runner_key, mean

RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
DNA = DATA / "edgeiq_runner_dna_v6_2.csv"
CAMPAIGN = DATA / "edgeiq_campaign_intelligence_engine_v1_1.csv"
FORM = DATA / "edgeiq_form_intelligence_v2.csv"
CONNECTION = DATA / "edgeiq_connection_intelligence_v2_1.csv"
SYNTHESIS = DATA / "edgeiq_intelligence_synthesis_engine_v1.csv"
SURFACE = DATA / "edgeiq_surface_intelligence_feed_v1.csv"
BIAS = DATA / "edgeiq_track_bias_engine_v1.csv"
OUT = DATA / "edgeiq_evidence_strength_model_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_evidence_strength_model_v2_summary.csv"
OUT_AUDIT = DATA / "edgeiq_evidence_strength_model_v2_audit.csv"


def map_runner(path):
    return {runner_key(r): r for r in read_csv(path)}


def map_race(path):
    return {race_key(r): r for r in read_csv(path)}


def score(value):
    u = text(value).upper()
    if any(t in u for t in ["EXCEPTIONAL", "ELITE", "STRONG", "HIGH", "GOOD", "IMPROVING", "POSITIVE"]):
        return 1.0
    if any(t in u for t in ["NEUTRAL", "MEDIUM", "BALANCED", "MIXED"]):
        return .55
    if any(t in u for t in ["LOW", "LIMITED", "WEAK", "POOR", "NO_EVIDENCE", "INSUFFICIENT", "BELOW"]):
        return .15
    return 0.0


def band(v):
    if v >= 78:
        return "VERY_STRONG"
    if v >= 62:
        return "STRONG"
    if v >= 42:
        return "MODERATE"
    if v > 0:
        return "THIN"
    return "MISSING"


def is_scratched(row):
    return "SCRATCH" in " ".join(text(row.get(k)).upper() for k in ["display_decision", "runner_status", "scratch_status", "is_scratched"])


def main():
    active = [r for r in read_csv(RUNNER) if not is_scratched(r)]
    dna, campaign, form, conn, synth = map_runner(DNA), map_runner(CAMPAIGN), map_runner(FORM), map_runner(CONNECTION), map_runner(SYNTHESIS)
    surface, bias = map_race(SURFACE), map_race(BIAS)
    rows = []
    race_scores = defaultdict(list)
    missing_pressure = defaultdict(list)
    for row in active:
        rk, rrk = runner_key(row), race_key(row)
        f = form.get(rk, {})
        values = {
            "dna_evidence": score(dna.get(rk, {}).get("dna_v6_2_band")),
            "campaign_evidence": score(campaign.get(rk, {}).get("campaign_profile_band")),
            "form_evidence": score(f.get("evidence_quality")),
            "performance_evidence": score(f.get("performance_intelligence_label")),
            "connection_evidence": score(conn.get(rk, {}).get("connection_band")),
            "history_evidence": 1.0 if text(f.get("recent_runs_found")) not in {"", "0"} else .0,
            "synthesis_alignment": score(synth.get(rk, {}).get("confidence_band")),
            "surface_evidence": .7 if text(surface.get(rrk, {}).get("surface_delta")) not in {"", "UNKNOWN"} else .0,
            "bias_evidence": .7 if text(bias.get(rrk, {}).get("inside_outside_advantage")) not in {"", "UNKNOWN"} else .0,
        }
        missing = sum(1 for v in values.values() if v <= 0)
        strength = mean(list(values.values())) * 100
        race_scores[rrk].append(strength)
        missing_pressure[rrk].append(missing)
        rows.append({
            "race_date": rrk[0], "track": text(row.get("track")), "race_no": rrk[2], "horse": text(row.get("horse")),
            **{k: f"{v:.2f}" for k, v in values.items()},
            "evidence_strength_score": f"{strength:.1f}",
            "evidence_strength_band": band(strength),
            "missing_evidence_count": missing,
            "race_evidence_strength": "",
            "race_missing_evidence_pressure": "",
        })
    aggregates = {rk: (mean(vals), mean(missing_pressure[rk])) for rk, vals in race_scores.items()}
    for row in rows:
        rk = (row["race_date"], clean(row["track"]), row["race_no"])
        row["race_evidence_strength"] = f"{aggregates[rk][0]:.1f}"
        row["race_missing_evidence_pressure"] = f"{aggregates[rk][1]:.2f}"
    audit = [{"race_date": k[0], "track_key": k[1], "race_no": k[2], "race_evidence_strength": f"{v[0]:.1f}", "race_missing_evidence_pressure": f"{v[1]:.2f}"} for k, v in aggregates.items()]
    summary = [{"metric": "runner_rows", "value": len(rows)}, {"metric": "race_rows", "value": len(aggregates)}, {"metric": "avg_evidence_strength", "value": f"{mean([float(r['evidence_strength_score']) for r in rows]):.1f}"}]
    write_csv(OUT, rows, list(rows[0].keys()) if rows else [])
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
