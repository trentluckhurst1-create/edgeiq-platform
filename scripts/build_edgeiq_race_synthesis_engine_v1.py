import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
CHAOS = DATA / "edgeiq_chaos_index_v1.csv"
OPPORTUNITY = DATA / "edgeiq_opportunity_score_v1.csv"
SURFACE = DATA / "edgeiq_surface_intelligence_feed_v1.csv"
BIAS = DATA / "edgeiq_track_bias_engine_v1.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_fallback_engine_v1.csv"

OUT = DATA / "edgeiq_race_synthesis_engine_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_race_synthesis_engine_v1_summary.csv"


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text(value):
    return str(value or "").strip()


def clean(value):
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def num(value, fallback=0.0):
    try:
        raw = text(value).replace("%", "").replace("$", "").replace(",", "")
        return float(raw) if raw else fallback
    except ValueError:
        return fallback


def race_date(row):
    return text(row.get("race_date") or row.get("current_race_date") or row.get("date"))


def race_no(row):
    return text(row.get("race_no") or row.get("race_number") or row.get("race"))


def race_key(row):
    return (race_date(row), clean(row.get("track")), race_no(row))


def is_scratched(row):
    return "SCRATCH" in " ".join(text(row.get(k)).upper() for k in ["display_decision", "runner_status", "scratch_status", "is_scratched"])


def thesis(chaos, opp, surface_delta, bias_read, pressure):
    parts = []
    if chaos >= 7:
        parts.append("high-chaos race")
    elif chaos >= 5:
        parts.append("moderate-chaos race")
    else:
        parts.append("controlled race shape")
    if opp >= 7:
        parts.append("strong opportunity profile")
    elif opp >= 5:
        parts.append("live opportunity profile")
    if surface_delta and surface_delta != "UNKNOWN":
        parts.append(f"surface read {surface_delta.lower().replace('_', ' ')}")
    if bias_read and bias_read != "UNKNOWN":
        parts.append(f"bias read {bias_read.lower()}")
    if pressure:
        parts.append(f"pace pressure {pressure}")
    return "; ".join(parts).capitalize() + "."


def main():
    active = [r for r in read_csv(RUNNER) if not is_scratched(r)]
    races = {}
    for row in active:
        races.setdefault(race_key(row), row)
    chaos = {race_key(r): r for r in read_csv(CHAOS)}
    opp = {race_key(r): r for r in read_csv(OPPORTUNITY)}
    surface = {race_key(r): r for r in read_csv(SURFACE)}
    bias = {race_key(r): r for r in read_csv(BIAS)}
    shape = {race_key(r): r for r in read_csv(RACE_SHAPE)}
    rows = []
    counts = Counter()
    for key, race in sorted(races.items()):
        c = chaos.get(key, {})
        o = opp.get(key, {})
        s = surface.get(key, {})
        b = bias.get(key, {})
        sh = shape.get(key, {})
        chaos_value = num(c.get("chaos_index"))
        opp_value = num(o.get("opportunity_score"))
        overall = thesis(chaos_value, opp_value, text(s.get("surface_delta")), text(b.get("inside_outside_advantage")), text(sh.get("pressure_risk") or sh.get("early_pressure_score")))
        regime = "HIGH_VARIANCE" if chaos_value >= 7 else "OPPORTUNITY_RACE" if opp_value >= 7 else "STANDARD"
        counts[regime] += 1
        rows.append({
            "race_date": key[0],
            "track": text(race.get("track")),
            "race_no": key[2],
            "chaos_index": f"{chaos_value:.2f}",
            "chaos_band": text(c.get("chaos_band")),
            "opportunity_score": f"{opp_value:.2f}",
            "opportunity_band": text(o.get("opportunity_band")),
            "surface_delta": text(s.get("surface_delta")),
            "edgeiq_condition": text(s.get("edgeiq_condition")),
            "bias": text(b.get("inside_outside_advantage")),
            "lane_bias": text(b.get("lane_bias")),
            "market_efficiency_placeholder": "RESEARCH_PENDING",
            "pace_pressure": text(sh.get("pressure_risk") or sh.get("early_pressure_score")),
            "race_regime": regime,
            "overall_race_thesis": overall,
        })
    write_csv(OUT, rows, list(rows[0].keys()) if rows else [])
    summary = [{"metric": "race_rows", "value": len(rows)}] + [{"metric": f"regime::{k}", "value": v} for k, v in counts.most_common()]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
