import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
DNA = DATA / "edgeiq_runner_dna_v6_2.csv"
CAMPAIGN = DATA / "edgeiq_campaign_intelligence_engine_v1_1.csv"
FORM = DATA / "edgeiq_form_intelligence_v2.csv"
CONNECTION = DATA / "edgeiq_connection_intelligence_v2_1.csv"
CHAOS = DATA / "edgeiq_chaos_index_v1.csv"
OPPORTUNITY = DATA / "edgeiq_opportunity_score_v1.csv"
SURFACE = DATA / "edgeiq_surface_intelligence_feed_v1.csv"
BIAS = DATA / "edgeiq_track_bias_engine_v1.csv"
PRICING = DATA / "edgeiq_probability_research_v5_2_guarded_temperature.csv"

OUT = DATA / "edgeiq_intelligence_synthesis_engine_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_intelligence_synthesis_engine_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_intelligence_synthesis_engine_v1_audit.csv"


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


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def num(value: object, fallback=0.0) -> float:
    try:
        raw = text(value).replace("%", "").replace("$", "").replace(",", "")
        return float(raw) if raw else fallback
    except ValueError:
        return fallback


def race_date(row):
    return text(row.get("race_date") or row.get("current_race_date") or row.get("date") or row.get("_date"))


def race_no(row):
    return text(row.get("race_no") or row.get("race_number") or row.get("race") or row.get("_race"))


def horse_key(row):
    return clean(row.get("horse_key") or row.get("horse"))


def runner_key(row):
    return (race_date(row), clean(row.get("track")), race_no(row), horse_key(row))


def race_key(row):
    return (race_date(row), clean(row.get("track")), race_no(row))


def is_scratched(row):
    return "SCRATCH" in " ".join(text(row.get(k)).upper() for k in ["display_decision", "runner_status", "scratch_status", "is_scratched"])


def band_score(value) -> int:
    upper = text(value).upper()
    if any(tok in upper for tok in ["EXCEPTIONAL", "ELITE", "STRONG CASE", "STRONG", "HIGH", "GOOD", "IMPROVING", "POSITIVE"]):
        return 1
    if any(tok in upper for tok in ["BELOW", "POOR", "WEAK", "LOW", "RISK", "NO_EVIDENCE", "NO EVIDENCE"]):
        return -1
    return 0


def confidence_band(score, evidence_count, contradictions):
    if evidence_count < 3:
        return "INSUFFICIENT_EVIDENCE"
    if contradictions >= 3:
        return "CONFLICTING_SIGNALS"
    if score >= 75:
        return "EXCEPTIONAL_ALIGNMENT"
    if score >= 58:
        return "STRONG_ALIGNMENT"
    if contradictions:
        return "CONFLICTING_SIGNALS"
    return "MIXED_SIGNALS"


def narrative(band, positives, negatives):
    if band == "EXCEPTIONAL_ALIGNMENT":
        return "Multiple intelligence layers align strongly."
    if band == "STRONG_ALIGNMENT":
        return "Multiple intelligence layers align."
    if band == "CONFLICTING_SIGNALS":
        return f"Signals conflict; proceed cautiously. Positive layers: {positives}; risk layers: {negatives}."
    if band == "INSUFFICIENT_EVIDENCE":
        return "Insufficient evidence across intelligence layers for a confident synthesis."
    return "Mixed signals across the intelligence stack."


def main():
    active = [row for row in read_csv(RUNNER) if not is_scratched(row)]
    maps = {
        "dna": {runner_key(r): r for r in read_csv(DNA)},
        "campaign": {runner_key(r): r for r in read_csv(CAMPAIGN)},
        "form": {runner_key(r): r for r in read_csv(FORM)},
        "connection": {runner_key(r): r for r in read_csv(CONNECTION)},
        "pricing": {(clean(r.get("track")), race_no(r), horse_key(r)): r for r in read_csv(PRICING)},
    }
    chaos = {race_key(r): r for r in read_csv(CHAOS)}
    opp = {race_key(r): r for r in read_csv(OPPORTUNITY)}
    surface = {race_key(r): r for r in read_csv(SURFACE)}
    bias = {race_key(r): r for r in read_csv(BIAS)}
    rows, audit = [], []
    counts = Counter()
    for row in active:
        key = runner_key(row)
        rkey = race_key(row)
        layer_scores = {
            "dna": band_score(maps["dna"].get(key, {}).get("dna_v6_2_band")),
            "campaign": band_score(maps["campaign"].get(key, {}).get("campaign_profile_band")),
            "form": band_score(maps["form"].get(key, {}).get("evidence_quality")),
            "performance": band_score(maps["form"].get(key, {}).get("performance_intelligence_label")),
            "connections": band_score(maps["connection"].get(key, {}).get("connection_band")),
            "surface": 0 if text(surface.get(rkey, {}).get("surface_delta")) in {"UNKNOWN", ""} else 1,
            "bias": 0 if text(bias.get(rkey, {}).get("track_bias_band")) in {"UNKNOWN", ""} else 1,
            "chaos": -1 if num(chaos.get(rkey, {}).get("chaos_index")) >= 7 else 0,
            "opportunity": 1 if num(opp.get(rkey, {}).get("opportunity_score")) >= 5 else 0,
        }
        pricing_row = maps["pricing"].get((clean(row.get("track")), race_no(row), horse_key(row)), {})
        if pricing_row and num(pricing_row.get("v5_2_probability")) > num(pricing_row.get("production_probability")):
            layer_scores["pricing_research"] = 1
        elif pricing_row:
            layer_scores["pricing_research"] = 0
        positives = [name for name, score in layer_scores.items() if score > 0]
        negatives = [name for name, score in layer_scores.items() if score < 0]
        evidence_count = sum(1 for score in layer_scores.values() if score != 0)
        contradiction_count = min(len(positives), len(negatives))
        raw = 50 + (sum(layer_scores.values()) * 8)
        align = max(0, min(100, raw - contradiction_count * 6))
        band = confidence_band(align, evidence_count, contradiction_count)
        counts[band] += 1
        rows.append({
            "race_date": rkey[0],
            "track": text(row.get("track")),
            "race_no": rkey[2],
            "horse": text(row.get("horse")),
            "intelligence_alignment_score": f"{align:.1f}",
            "evidence_strength": evidence_count,
            "contradiction_count": contradiction_count,
            "confidence_band": band,
            "overall_read": narrative(band, ",".join(positives) or "none", ",".join(negatives) or "none"),
            "positive_layers": ";".join(positives),
            "risk_layers": ";".join(negatives),
        })
        audit.append({
            "race_date": rkey[0],
            "track": text(row.get("track")),
            "race_no": rkey[2],
            "horse": text(row.get("horse")),
            **{f"{name}_score": score for name, score in layer_scores.items()},
        })
    write_csv(OUT, rows, list(rows[0].keys()) if rows else [])
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    summary = [{"metric": "runner_rows", "value": len(rows)}] + [{"metric": f"band::{k}", "value": v} for k, v in counts.most_common()]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
