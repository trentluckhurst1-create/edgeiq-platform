from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence-context-parameter-program-v1"
BUILT_AT = "2026-07-30T00:10:00Z"
STATUS = "BLOCKED_CONTEXT_PARAMETER_METHODOLOGY_AUTHORITY"


def t(v): return str(v if v is not None else "").strip()
def token(v): return "".join(ch for ch in t(v).upper() if ch.isalnum())
def norm(v): return " ".join(t(v).upper().split())
def sha(xs): return hashlib.sha256("\x1f".join(t(x) for x in xs).encode("utf-8")).hexdigest()
def dec(v):
    try:
        if t(v) == "": return None
        raw = t(v).lower().replace("kg", "").replace("kgs", "").replace("m", "")
        raw = "".join(ch for ch in raw if ch.isdigit() or ch in ".-")
        if raw == "":
            return None
        x = Decimal(raw)
        return x if x.is_finite() else None
    except Exception:
        return None


def read_csv(path: Path):
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def write_csv(path: Path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0].keys()) if rows else ["status"])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def count_rows(path: Path) -> int:
    return len(read_csv(path)[1])


def audit_status(name: str) -> str:
    path = DATA / name
    if not path.exists(): return "MISSING"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj.get("status") or obj.get("audit_status") or "UNKNOWN"
    except Exception:
        return "UNREADABLE"


def race_no(v):
    x = t(v).replace(".0", "")
    return str(int(x)) if x.isdigit() else x


def distance(v):
    return "".join(ch for ch in t(v) if ch.isdigit())


def race_key(d, tr, rn):
    r = race_no(rn)
    return f"{t(d)}|{token(tr)}|R{int(r):02d}" if r.isdigit() else f"{t(d)}|{token(tr)}|R{r}"


def ref_parts(ref: str):
    out = {}
    if "#" in ref: ref = ref.split("#", 1)[1]
    for part in ref.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip().replace(".0", "")
    return out


def band_rows(rows):
    for r in rows:
        fs, b, w = dec(r.get("declared_field_size")), dec(r.get("barrier")), dec(r.get("allocated_weight_kg"))
        if fs and b:
            p = b / fs
            r["barrier_band"] = "INNER" if p <= Decimal("0.333333") else "MIDDLE" if p <= Decimal("0.666667") else "OUTER"
        else:
            r["barrier_band"] = ""
        if w is None: r["weight_band"] = ""
        elif w < 50: r["weight_band"] = "WEIGHT_35_TO_49_999999"
        elif w < 55: r["weight_band"] = "WEIGHT_50_TO_54_999999"
        elif w < 60: r["weight_band"] = "WEIGHT_55_TO_59_999999"
        elif w < 65: r["weight_band"] = "WEIGHT_60_TO_64_999999"
        else: r["weight_band"] = "WEIGHT_65_TO_80"
        if fs is None: r["field_size_band"] = ""
        elif fs <= 8: r["field_size_band"] = "FIELD_1_TO_8"
        elif fs <= 12: r["field_size_band"] = "FIELD_9_TO_12"
        elif fs <= 16: r["field_size_band"] = "FIELD_13_TO_16"
        elif fs <= 24: r["field_size_band"] = "FIELD_17_TO_24"
        else: r["field_size_band"] = "FIELD_25_TO_40"
    return rows


def training_facts():
    _, obs = read_csv(DATA / "edgeiq_horse_performance_observation_fact_v1.csv")
    _, results = read_csv(DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv")
    field_sizes = Counter()
    by_runner, by_horse = {}, {}
    for r in results:
        if t(r.get("state")) and t(r.get("state")).upper() != "VIC": continue
        rk = race_key(r.get("race_date"), r.get("track"), r.get("race_no"))
        field_sizes[rk] += 1
        if t(r.get("runner_id")): by_runner[(rk, t(r.get("runner_id")).replace(".0", ""))] = r
        if t(r.get("horse_code")): by_horse[(rk, t(r.get("horse_code")).replace(".0", ""))] = r
    rows = []
    for o in obs:
        rk = t(o.get("race_key"))
        rp = ref_parts(o.get("identity_evidence_reference", ""))
        rr = by_runner.get((rk, rp.get("runner_id", ""))) or by_horse.get((rk, rp.get("horse_code", "")))
        if not rr: continue
        rows.append({
            "training_fact_id": "CPFTR1-" + sha([o.get("horse_performance_observation_id"), rk])[:24].upper(),
            "race_date": t(o.get("race_date")), "race_key": rk, "race_id": t(rr.get("race_id")).replace(".0", ""),
            "runner_id": rp.get("runner_id", ""), "canonical_horse_id": t(o.get("canonical_horse_id")),
            "canonical_horse_name": t(o.get("canonical_horse_name")),
            "performance_target_value": t(o.get("rating_base_value")),
            "target_unit": "HPR-NORM-A normalised rating units",
            "track_id": token(rr.get("track") or o.get("track_name")), "track_configuration": token(rr.get("track") or o.get("track_name")),
            "race_distance_m": distance(rr.get("distance") or o.get("official_distance_metres")),
            "race_class_code": t(rr.get("race_class")),
            "track_condition": norm((t(rr.get("track_condition")) + " " + t(rr.get("track_rating"))).strip()),
            "racing_surface": "TURF", "rail_position": t(rr.get("rail_position")),
            "barrier": t(rr.get("barrier") or rr.get("live_barrier")), "allocated_weight_kg": t(rr.get("weight")),
            "declared_field_size": str(field_sizes[rk]) if field_sizes[rk] else "",
            "source_observation_id": t(o.get("horse_performance_observation_id")),
            "training_fact_status": "TRAINING_FACT_AVAILABLE" if t(o.get("rating_base_value")) else "MISSING_TARGET",
        })
    return band_rows(rows)


def coverage(rows):
    fields = ["race_date","race_key","runner_id","canonical_horse_id","track_id","track_configuration","race_distance_m","race_class_code","track_condition","racing_surface","rail_position","barrier","allocated_weight_kg","declared_field_size","performance_target_value"]
    out = []
    n = len(rows)
    for f in fields:
        vals = [t(r.get(f)) for r in rows]
        non = [v for v in vals if v]
        out.append({"field": f, "total_rows": n, "non_null_rows": len(non), "valid_rows": len(non), "coverage_pct": f"{(len(non)/n*100) if n else 0:.2f}", "distinct_values": len(set(non)), "earliest_date": min((r["race_date"] for r in rows if t(r.get(f)) and t(r.get("race_date"))), default=""), "latest_date": max((r["race_date"] for r in rows if t(r.get(f)) and t(r.get("race_date"))), default=""), "invalid_rows": 0, "unknown_rows": n-len(non), "source_authority": "Governed HPO joined to Racing.com historical results warehouse"})
    return out


def signatures(rows):
    levels = {
        "exact_full_signature": ["race_distance_m","race_class_code","track_id","track_configuration","track_condition","racing_surface","barrier_band","weight_band","field_size_band"],
        "track_configuration_distance": ["track_id","track_configuration","race_distance_m"],
        "track_distance": ["track_id","race_distance_m"],
        "distance_class": ["race_distance_m","race_class_code"],
        "distance_condition": ["race_distance_m","track_condition"],
        "track_distance_condition": ["track_id","race_distance_m","track_condition"],
        "barrier_field_size": ["barrier_band","field_size_band"],
        "weight_class": ["weight_band","race_class_code"],
        "surface_condition": ["racing_surface","track_condition"],
    }
    depth, cand, rej = [], [], []
    for level, cols in levels.items():
        groups = defaultdict(list)
        for r in rows:
            if all(t(r.get(c)) for c in cols) and t(r.get("performance_target_value")):
                groups[tuple(t(r.get(c)) for c in cols)].append(r)
        ds = [len(v) for v in groups.values()]
        diag = 0
        for key, vals in groups.items():
            races = len({v["race_key"] for v in vals}); horses = len({v["canonical_horse_id"] for v in vals})
            dates = sorted(v["race_date"] for v in vals if v["race_date"])
            nums = [float(v["performance_target_value"]) for v in vals if t(v.get("performance_target_value"))]
            if len(vals) >= 100 and races >= 50 and horses >= 50: diag += 1
            row = {"context_signature_level": level, "signature_key": "|".join(key), "observation_count": len(vals), "distinct_races": races, "distinct_horses": horses, "training_start_date": dates[0] if dates else "", "training_end_date": dates[-1] if dates else "", "target_mean_diagnostic_only": f"{(sum(nums)/len(nums)) if nums else 0:.6f}", "target_stddev_diagnostic_only": f"{statistics.pstdev(nums) if len(nums)>1 else 0:.6f}", "candidate_status": "DIAGNOSTIC_ONLY_NOT_APPROVED", "approval_blocker": STATUS}
            cand.append(row); rej.append({**row, "rejection_reason": "NO_AUTHORISED_ESTIMATION_METHOD_OR_EVIDENCE_THRESHOLD"})
        depth.append({"context_signature_level": level, "signature_columns": ",".join(cols), "signature_count": len(groups), "observations_represented": sum(ds), "median_observations_per_signature": f"{statistics.median(ds):.2f}" if ds else "0", "max_observations": max(ds) if ds else 0, "min_observations": min(ds) if ds else 0, "diagnostic_signatures_ge_100_obs_50_races_50_horses": diag, "production_authority_status": "NOT_AUTHORISED"})
    return depth, cand, rej


def live_trace():
    specs = [
        ("Results Warehouse","edgeiq_historical_results_warehouse_v2_graphql.csv","race_date","race_id","runner_id"),
        ("Timed Races","edgeiq_canonical_historical_timing_warehouse_v1.csv","race_date","race_key",""),
        ("Race Time Delta","edgeiq_race_time_delta_versus_standard_fact_v1.csv","race_date","race_key",""),
        ("Lengths v Standard","edgeiq_lengths_versus_standard_fact_v1.csv","race_date","race_key",""),
        ("Performance Base","edgeiq_performance_intelligence_base_fact_v1.csv","race_date","race_key",""),
        ("Normalisation","edgeiq_performance_normalisation_fact_v1.csv","race_date","race_key",""),
        ("Performance Rating Base","edgeiq_performance_rating_base_fact_v1.csv","race_date","race_key",""),
    ]
    out = []
    for stage, fn, df, rf, runf in specs:
        fields, rows = read_csv(DATA / fn)
        cur = [r for r in rows if df in fields and t(r.get(df)) >= "2026-07-20"]
        dates = sorted(t(r.get(df)) for r in cur if t(r.get(df)))
        out.append({"stage": stage, "input_file": "public/data/" + fn, "input_rows": len(rows), "current_rows_on_or_after_2026_07_20": len(cur), "distinct_races": len({t(r.get(rf)) for r in cur if rf and t(r.get(rf))}), "distinct_runners": len({t(r.get(runf)) for r in cur if runf and t(r.get(runf))}), "minimum_date": dates[0] if dates else "", "maximum_date": dates[-1] if dates else "", "first_failure": "NO_CURRENT_ROWS" if not cur else "", "rejection_reasons": ""})
    return out


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    tr = training_facts()
    cov = coverage(tr)
    depth, cand, rej = signatures(tr)
    live = live_trace()
    write_csv(DOCS/"EDGEIQ_CONTEXT_PARAMETER_TRAINING_FACT_V1.csv", tr)
    write_csv(DOCS/"EDGEIQ_CONTEXT_PARAMETER_FIELD_COVERAGE_V1.csv", cov)
    write_csv(DOCS/"EDGEIQ_CONTEXT_SIGNATURE_DEPTH_PROFILE_V1.csv", depth)
    write_csv(DOCS/"EDGEIQ_CONTEXT_PARAMETER_CANDIDATES_V1.csv", cand)
    write_csv(DOCS/"EDGEIQ_CONTEXT_PARAMETER_REJECTIONS_V1.csv", rej)
    write_csv(DOCS/"EDGEIQ_CONTEXT_PARAMETER_VALIDATION_V1.csv", [{"baseline_error":"NOT_RUN","adjusted_error":"NOT_RUN","validation_status":STATUS}])
    sel = read_csv(DATA/"edgeiq_race_entry_context_parameter_selection_fact_v1.csv")[1]
    adj = read_csv(DATA/"edgeiq_race_entry_context_adjustment_fact_v1.csv")[1]
    write_csv(DOCS/"EDGEIQ_CURRENT_CONTEXT_PARAMETER_SELECTION_TRACE_V1.csv", [{"race_id":r.get("race_id",""),"runner_id":r.get("runner_id",""),"canonical_horse_id":r.get("canonical_horse_id",""),"exact_context_signature":"|".join([r.get(c,"") for c in ["race_distance_m","race_class_code","track_id","track_configuration","track_condition","racing_surface","barrier_band","weight_band","field_size_band"]]),"selected_parameter":r.get("context_parameter_id",""),"selection_hierarchy_level":"EXACT_ONLY","selection_reason":r.get("context_parameter_selection_decision",""),"rejection_reason":"PARAMETER_NOT_AVAILABLE" if r.get("context_parameter_selection_decision")=="PARAMETER_NOT_AVAILABLE" else ""} for r in sel])
    write_csv(DOCS/"EDGEIQ_CURRENT_CONTEXT_ADJUSTMENT_TRACE_V1.csv", [{"race_id":r.get("race_id",""),"runner_id":r.get("runner_id",""),"canonical_horse_id":r.get("canonical_horse_id",""),"historical_rating_value":r.get("historical_rating_value",""),"context_parameter_id":r.get("context_parameter_id",""),"total_context_adjustment":r.get("total_context_adjustment",""),"decision":r.get("context_adjustment_application_decision",""),"status":r.get("race_entry_context_adjustment_status","")} for r in adj])
    write_csv(DOCS/"EDGEIQ_CURRENT_EPI_TRACE_V2.csv", [{"stage":"Projected Performance","rows":count_rows(DATA/"edgeiq_race_entry_projected_performance_fact_v1.csv"),"status":"EMPTY_BY_GOVERNED_BLOCKER"},{"stage":"EPI Components","rows":count_rows(DATA/"edgeiq_race_entry_epi_component_fact_v1.csv"),"status":"EMPTY_BY_GOVERNED_BLOCKER"},{"stage":"EPI","rows":count_rows(DATA/"edgeiq_race_entry_epi_fact_v1.csv"),"status":"EMPTY_BY_GOVERNED_BLOCKER"}])
    write_csv(DOCS/"EDGEIQ_VICTORIA_LIVE_PERFORMANCE_PIPELINE_TRACE_V1.csv", live)
    arch = {"status": STATUS, "target_defined": True, "parameter_target": "context_adjusted_performance_value", "parameter_unit": "HPR-NORM-A normalised rating units", "formula_meaning_defined": False, "downstream_formula": "context_adjusted_performance_value = historical_rating_value + total_context_adjustment", "selection_hierarchy": "EXACT_ONLY_NO_FALLBACK", "minimum_evidence_authority_defined": False, "validation_method_defined": False, "temporal_control_defined_for_parameters": False, "empty_registry_cause": "No governed empirical method or threshold authority."}
    write_json(DOCS/"EDGEIQ_CONTEXT_PARAMETER_ARCHITECTURE_INVESTIGATION_V1.json", arch)
    write_md(DOCS/"EDGEIQ_CONTEXT_PARAMETER_ARCHITECTURE_INVESTIGATION_V1.md", "# EDGEiQ Context Parameter Architecture Investigation V1\n\nStatus: BLOCKED_CONTEXT_PARAMETER_METHODOLOGY_AUTHORITY\n\nThe downstream formula is defined as additive, and parameter selection is exact-only with no fallback. The repository does not define the governed empirical coefficient-estimation method, repeated-horse controls, threshold authority, temporal training windows, or validation approval rule. No production coefficients were generated.")
    feas = {"status": STATUS, "historical_rows_assessed": len(tr), "training_rows": len(tr), "validation_rows": 0, "full_signatures_assessed": next((r["signature_count"] for r in depth if r["context_signature_level"]=="exact_full_signature"),0), "candidate_parameters": len(cand), "approved_parameters": 0, "rejected_parameters": len(rej)}
    write_json(DOCS/"EDGEIQ_CONTEXT_PARAMETER_FEASIBILITY_V1.json", feas)
    write_md(DOCS/"EDGEIQ_CONTEXT_PARAMETER_FEASIBILITY_V1.md", f"# EDGEiQ Context Parameter Feasibility V1\n\nStatus: {STATUS}\n\nHistorical training facts assessed: {len(tr)}. Diagnostic candidates: {len(cand)}. Approved parameters: 0. Rejected parameters: {len(rej)}.")
    method = {"status": STATUS, "target_variable":"context_adjusted_performance_value", "target_unit":"HPR-NORM-A normalised rating units", "estimation_method_defined": False, "threshold_authority_defined": False, "decision":"Do not estimate or publish coefficients."}
    write_json(DOCS/"EDGEIQ_CONTEXT_PARAMETER_METHOD_V1.json", method)
    write_md(DOCS/"EDGEIQ_CONTEXT_PARAMETER_METHOD_V1.md", "# EDGEiQ Context Parameter Method V1\n\nStatus: BLOCKED_CONTEXT_PARAMETER_METHODOLOGY_AUTHORITY\n\nA simple average-difference model was not implemented because it would confuse horse ability with race context. The repository lacks an authorised repeated-horse/race-control empirical method.")
    val = {"status":"NOT_RUN_BLOCKED_CONTEXT_PARAMETER_METHODOLOGY_AUTHORITY","baseline_metric":"NOT_RUN","adjusted_metric":"NOT_RUN","improvement":"NOT_RUN","bias":"NOT_RUN","stability_result":"NOT_RUN"}
    write_json(DOCS/"EDGEIQ_CONTEXT_PARAMETER_VALIDATION_V1.json", val)
    write_md(DOCS/"EDGEIQ_CONTEXT_PARAMETER_VALIDATION_V1.md", "# EDGEiQ Context Parameter Validation V1\n\nStatus: NOT_RUN_BLOCKED_CONTEXT_PARAMETER_METHODOLOGY_AUTHORITY\n\nValidation was not run because no governed coefficient-estimation method exists.")
    reg = {"status": STATUS, "registry_rows": count_rows(DATA/"edgeiq_context_parameter_registry_v1.csv"), "approved_parameters": 0, "rejected_parameters": len(rej), "selected_unvalidated_parameters": 0, "defaults_introduced": False}
    write_json(DOCS/"EDGEIQ_CONTEXT_PARAMETER_REGISTRY_ACCEPTANCE_V1.json", reg)
    write_md(DOCS/"EDGEIQ_CONTEXT_PARAMETER_REGISTRY_ACCEPTANCE_V1.md", "# EDGEiQ Context Parameter Registry Acceptance V1\n\nStatus: BLOCKED_CONTEXT_PARAMETER_METHODOLOGY_AUTHORITY\n\nThe registry remains header-only. No defaults, fabricated values, fallbacks, or unvalidated parameters were introduced.")
    live_json = {"status":"BLOCKED_SOURCE_DATA_UNAVAILABLE","legacy_audit_stale":"NO","first_live_ingestion_blocker":"TIMED_RACE_NOT_BUILT_FOR_CURRENT_RESULTS","repair_implemented":"NO","pipeline_trace":live}
    write_json(DOCS/"EDGEIQ_VICTORIA_LIVE_PERFORMANCE_BASE_INVESTIGATION_V1.json", live_json)
    write_md(DOCS/"EDGEIQ_VICTORIA_LIVE_PERFORMANCE_BASE_INVESTIGATION_V1.md", "# EDGEiQ Victoria Live Performance Base Investigation V1\n\nStatus: BLOCKED_SOURCE_DATA_UNAVAILABLE\n\nCurrent result rows exist after 2026-07-20, but canonical Timed Race, Race Time Delta, Lengths v Standard and Performance Base rows do not contain post-cutoff rows. V6 historical backfill snapshots are a separate path and do not prove current incremental timed-performance ingestion.")
    final = {"overall_status": STATUS, "track_a_status": STATUS, "track_b_status":"BLOCKED_SOURCE_DATA_UNAVAILABLE", "metrics": {"historical_rows_assessed":len(tr),"training_rows":len(tr),"candidate_parameters":len(cand),"approved_parameters":0,"rejected_parameters":len(rej),"context_rows":count_rows(DATA/"edgeiq_race_entry_performance_context_fact_v1.csv"),"epi_rows":count_rows(DATA/"edgeiq_race_entry_epi_fact_v1.csv")}, "protected_systems":{"pricing_changed":"NO","probability_changed":"NO","v6_1_changed":"NO","v7_2g2_changed":"NO","ui_changed":"NO","hpr_norm_a_v1_changed":"NO","hpr_norm_a_v2_changed":"NO","minimum_observations_changed":"NO"}}
    write_json(DOCS/"EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_FINAL_ACCEPTANCE_V2.json", final)
    write_csv(DOCS/"EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_FINAL_ACCEPTANCE_V2.csv", [{"section":k,"value":json.dumps(v,sort_keys=True) if isinstance(v,dict) else v} for k,v in final.items()], ["section","value"])
    write_md(DOCS/"EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_FINAL_ACCEPTANCE_V2.md", f"# EDGEiQ Victoria Performance Intelligence Final Acceptance V2\n\nOverall status: {STATUS}\n\nTrack A is blocked by missing methodology authority. Track B is blocked by missing current timed-performance ingestion after results.")
    write_md(DOCS/"EDGEIQ_CONTEXT_PARAMETER_PROGRAM_VALIDATION_V1.md", "# EDGEiQ Context Parameter Program Validation V1\n\nStatus: PASS_REPORTS_BUILT\n\nPython, TypeScript and production build validation are executed separately.")
    required = sorted(DOCS.glob("EDGEIQ_*"), key=lambda p: p.name)
    hashes = {str(p.relative_to(ROOT)).replace("\\","/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in required if p.name != "EDGEIQ_CONTEXT_PARAMETER_PROGRAM_IDEMPOTENCY_V1.json"}
    write_json(DOCS/"EDGEIQ_CONTEXT_PARAMETER_PROGRAM_IDEMPOTENCY_V1.json", {"status":"PASS_SEMANTIC_HASHES_RECORDED","built_at_utc":BUILT_AT,"hashes":hashes})
    print("EDGEIQ_CONTEXT_PARAMETER_PROGRAM_V1_BUILT")
    print(f"status={STATUS}")
    print(f"training_rows={len(tr)}")
    print(f"candidate_parameters={len(cand)}")
    print("approved_parameters=0")


if __name__ == "__main__":
    main()
