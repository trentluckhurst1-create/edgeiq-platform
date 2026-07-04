from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_EPF = DATA / "edgeiq_epf_v1_1_guardrailed.csv"
INPUT_CURRENT_EPF = DATA / "edgeiq_current_epf_feed_v1_1.csv"
INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_SECTIONALS = DATA / "edgeiq_sectional_ability_engine_v3.csv"
INPUT_CLASS_STRENGTH = DATA / "edgeiq_class_strength_engine_v2.csv"

OUTPUT_MAIN = DATA / "edgeiq_hidden_gem_engine_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_hidden_gem_engine_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_hidden_gem_engine_v1_audit.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def clean_horse(value: object) -> str:
    txt = upper(value)
    return "".join(ch for ch in txt if ch.isalnum())


def parse_float(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("$", "").replace("kg", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return None


def parse_int(value: object) -> Optional[int]:
    num = parse_float(value)
    if num is None:
        return None
    return int(round(num))


def parse_date(value: object) -> Optional[datetime]:
    txt = clean(value)
    if txt == "":
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def is_active_runner(row: Dict[str, str]) -> bool:
    flags = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return not any(flag in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for flag in flags)


def load_sectional_lookup() -> Dict[str, Dict[str, str]]:
    if not INPUT_SECTIONALS.exists():
        return {}
    lookup: Dict[str, Dict[str, str]] = {}
    with INPUT_SECTIONALS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = clean_horse(row.get("horse_key")) or clean_horse(row.get("horse_name"))
            if key:
                lookup[key] = row
    return lookup


def load_class_strength_lookup() -> Dict[str, Dict[str, str]]:
    if not INPUT_CLASS_STRENGTH.exists():
        return {}
    lookup: Dict[str, Dict[str, str]] = {}
    with INPUT_CLASS_STRENGTH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = clean(row.get("race_class"))
            if key:
                lookup[key] = row
    return lookup


def hidden_gem_band(score: Optional[float]) -> str:
    if score is None:
        return "UNKNOWN"
    if score >= 70:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    if score >= 25:
        return "LOW"
    return "NO_SIGNAL"


def scoring_narrative(
    score: float,
    band: str,
    triggers: List[str],
    finish_position: Optional[int],
    beaten_margin: Optional[float],
    epf_display: Optional[float],
) -> str:
    if band in {"NO_SIGNAL", "UNKNOWN"}:
        if epf_display is None:
            return "No hidden-gem signal because guarded EPF evidence was unavailable."
        return (
            f"Finished {finish_position if finish_position is not None else 'N/A'} with display EPF "
            f"{epf_display:+.1f}L, but the run did not clear the hidden-gem trigger threshold."
        )
    trigger_text = "; ".join(triggers[:3]) if triggers else "signal present"
    beaten_txt = f"{beaten_margin:.1f}L" if beaten_margin is not None else "margin N/A"
    return (
        f"Finished {finish_position if finish_position is not None else 'N/A'} beaten {beaten_txt} with "
        f"display EPF {epf_display:+.1f}L. Hidden-gem score {score:.0f} from {trigger_text}."
    )


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def evidence_status(row: Dict[str, str], finish_position: Optional[int], beaten_margin: Optional[float]) -> str:
    if upper(row.get("epf_customer_safe_flag")) != "YES":
        return "REJECTED_NOT_CUSTOMER_SAFE"
    if upper(row.get("epf_confidence_band")) == "LOW":
        return "REJECTED_LOW_CONFIDENCE"
    if upper(row.get("race_type")) != "FLAT":
        return "REJECTED_NON_FLAT"
    if finish_position is None or finish_position <= 0:
        return "REJECTED_INVALID_FINISH"
    if finish_position == 1:
        return "REJECTED_WINNER"
    if finish_position < 4:
        return "REJECTED_PLACED"
    if beaten_margin is None:
        return "REJECTED_NO_MARGIN"
    if "ABNORMAL_FINISH_CODE" in upper(row.get("epf_guardrail_flag")):
        return "REJECTED_ABNORMAL_FINISH"
    return "EVALUATED"


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if not INPUT_EPF.exists():
        raise FileNotFoundError(INPUT_EPF)

    sectional_lookup = load_sectional_lookup()
    class_strength_lookup = load_class_strength_lookup()

    active_board_rows = []
    if INPUT_BOARD.exists():
        with INPUT_BOARD.open("r", encoding="utf-8-sig", newline="") as handle:
            active_board_rows = [row for row in csv.DictReader(handle) if is_active_runner(row)]

    current_epf_rows = []
    if INPUT_CURRENT_EPF.exists():
        with INPUT_CURRENT_EPF.open("r", encoding="utf-8-sig", newline="") as handle:
            current_epf_rows = list(csv.DictReader(handle))

    output_rows: List[Dict[str, object]] = []
    evidence_counts: Counter[str] = Counter()
    band_counts: Counter[str] = Counter()
    rejection_counts: Counter[str] = Counter()

    with INPUT_EPF.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            horse_key = clean_horse(row.get("horse_key")) or clean_horse(row.get("horse"))
            finish_position = parse_int(row.get("finish_position"))
            beaten_margin = parse_float(row.get("beaten_margin"))
            epf_display = parse_float(row.get("display_epf_lengths"))
            status = evidence_status(row, finish_position, beaten_margin)
            evidence_counts[status] += 1

            score: Optional[float] = None
            band = "UNKNOWN"
            triggers: List[str] = []

            if status == "EVALUATED":
                score = 0.0

                if epf_display is not None and epf_display >= 4.0 and finish_position is not None and finish_position >= 4:
                    score += 55.0
                    triggers.append("Strong EPF despite unplaced finish")
                elif epf_display is not None and epf_display >= 2.0 and finish_position is not None and finish_position >= 4:
                    score += 35.0
                    triggers.append("Positive EPF despite unplaced finish")
                elif epf_display is not None and epf_display > 0.0 and finish_position is not None and finish_position >= 4:
                    score += 18.0
                    triggers.append("Positive EPF despite finishing outside placings")

                if epf_display is not None and epf_display > 0.0 and beaten_margin is not None and beaten_margin >= 3.0:
                    score += 15.0
                    triggers.append("Held positive figure despite material beaten margin")

                if finish_position is not None and finish_position >= 6 and epf_display is not None and epf_display >= 2.0:
                    score += 10.0
                    triggers.append("Finish position worse than figure suggests")
                elif finish_position is not None and finish_position >= 8 and epf_display is not None and epf_display > 0.0:
                    score += 8.0
                    triggers.append("Deep finishing position but still positive figure")

                sectional_row = sectional_lookup.get(horse_key)
                sectional_score = parse_float(sectional_row.get("sectional_ability_score_v3")) if sectional_row else None
                sectional_conf = upper(sectional_row.get("sectional_confidence_band_v3")) if sectional_row else ""
                if sectional_score is not None and sectional_score >= 70 and sectional_conf not in {"LOW", ""}:
                    score += 8.0
                    triggers.append("Strong late-profile support from sectional ability")

                class_row = class_strength_lookup.get(clean(row.get("race_class")))
                class_strength = parse_float(class_row.get("class_strength_score_v2")) if class_row else None
                if class_strength is not None and class_strength >= 70:
                    score += 5.0
                    triggers.append("Performance came from stronger class context")

                if beaten_margin is not None and beaten_margin >= 8.0:
                    score -= 10.0
                if beaten_margin is not None and beaten_margin >= 12.0:
                    score -= 10.0

                if score < 0:
                    score = 0.0
                band = hidden_gem_band(score)
            else:
                rejection_counts[status] += 1
                score = 0.0
                band = "NO_SIGNAL" if status.startswith("REJECTED_") else "UNKNOWN"

            band_counts[band] += 1
            next_watch = "YES" if band in {"HIGH", "MEDIUM"} else "NO"
            output_rows.append(
                {
                    "race_date": clean(row.get("race_date")),
                    "track": upper(row.get("track")),
                    "race_no": clean(row.get("race_no")),
                    "horse": clean(row.get("horse")),
                    "horse_key": horse_key,
                    "finish_position": finish_position if finish_position is not None else "",
                    "beaten_margin": f"{beaten_margin:.3f}" if beaten_margin is not None else "",
                    "display_epf_lengths": f"{epf_display:.3f}" if epf_display is not None else "",
                    "epf_band": clean(row.get("display_epf_band")) or clean(row.get("epf_band")),
                    "hidden_gem_score": f"{score:.1f}" if score is not None else "",
                    "hidden_gem_band": band,
                    "trigger_1": triggers[0] if len(triggers) >= 1 else "",
                    "trigger_2": triggers[1] if len(triggers) >= 2 else "",
                    "trigger_3": triggers[2] if len(triggers) >= 3 else "",
                    "hidden_gem_narrative": scoring_narrative(score or 0.0, band, triggers, finish_position, beaten_margin, epf_display),
                    "next_start_watch_flag": next_watch,
                    "evidence_status": status,
                    "source_epf_confidence_band": clean(row.get("epf_confidence_band")),
                    "source_epf_customer_safe_flag": clean(row.get("epf_customer_safe_flag")),
                    "source_guardrail_flag": clean(row.get("epf_guardrail_flag")),
                    "race_class": clean(row.get("race_class")),
                    "built_at": built_at,
                }
            )

    signal_rows = [row for row in output_rows if row["hidden_gem_band"] in {"HIGH", "MEDIUM", "LOW"}]
    watch_rows = [row for row in output_rows if row["next_start_watch_flag"] == "YES"]

    active_horse_keys = {clean_horse(row.get("horse_key")) or clean_horse(row.get("horse")) for row in active_board_rows}
    active_watch_keys = {clean_horse(row["horse_key"]) for row in watch_rows if clean_horse(row["horse_key"]) in active_horse_keys}

    bendigo_active_keys = {
        clean_horse(row.get("horse_key")) or clean_horse(row.get("horse"))
        for row in active_board_rows
        if upper(row.get("track")) == "BENDIGO"
    }
    bendigo_watch_keys = {key for key in active_watch_keys if key in bendigo_active_keys}

    summary_row = {
        "status": "EDGEIQ_HIDDEN_GEM_ENGINE_V1_BUILT",
        "total_historical_rows_processed": len(output_rows),
        "hidden_gem_count": len(signal_rows),
        "high_count": band_counts.get("HIGH", 0),
        "medium_count": band_counts.get("MEDIUM", 0),
        "low_count": band_counts.get("LOW", 0),
        "no_signal_count": band_counts.get("NO_SIGNAL", 0),
        "unknown_count": band_counts.get("UNKNOWN", 0),
        "active_current_runners_with_prior_hidden_gem_signal": len(active_watch_keys),
        "bendigo_current_runners_with_prior_hidden_gem_signal": len(bendigo_watch_keys),
        "rejected_not_customer_safe": rejection_counts.get("REJECTED_NOT_CUSTOMER_SAFE", 0),
        "rejected_low_confidence": rejection_counts.get("REJECTED_LOW_CONFIDENCE", 0),
        "rejected_winner": rejection_counts.get("REJECTED_WINNER", 0),
        "rejected_placed": rejection_counts.get("REJECTED_PLACED", 0),
        "rejected_no_margin": rejection_counts.get("REJECTED_NO_MARGIN", 0),
        "readiness_verdict": "READY_WITH_GUARDRAILS" if len(watch_rows) > 0 else "NOT_READY",
        "built_at": built_at,
    }

    audit_rows: List[Dict[str, object]] = []
    for name, count in sorted(band_counts.items()):
        audit_rows.append({"audit_type": "BAND_COUNT", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(evidence_counts.items()):
        audit_rows.append({"audit_type": "EVIDENCE_STATUS", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(rejection_counts.items()):
        audit_rows.append({"audit_type": "FALSE_POSITIVE_GUARDRAIL", "audit_value": name, "count": count, "built_at": built_at})

    high_examples = sorted(
        [row for row in output_rows if row["hidden_gem_band"] == "HIGH"],
        key=lambda item: (-(parse_float(item.get("hidden_gem_score")) or 0.0), clean(item.get("race_date")), clean(item.get("horse"))),
    )[:10]
    for idx, row in enumerate(high_examples, start=1):
        audit_rows.append(
            {
                "audit_type": "HIGH_SIGNAL_EXAMPLE",
                "audit_value": f"{idx}. {row['horse']} {row['track']} R{row['race_no']} {row['hidden_gem_score']} {row['trigger_1']}",
                "count": "",
                "built_at": built_at,
            }
        )

    rejected_examples = [row for row in output_rows if row["evidence_status"].startswith("REJECTED_")][:10]
    for idx, row in enumerate(rejected_examples, start=1):
        audit_rows.append(
            {
                "audit_type": "REJECTED_EXAMPLE",
                "audit_value": f"{idx}. {row['horse']} {row['track']} R{row['race_no']} {row['evidence_status']}",
                "count": "",
                "built_at": built_at,
            }
        )

    fields = list(output_rows[0].keys()) if output_rows else [
        "race_date",
        "track",
        "race_no",
        "horse",
        "hidden_gem_score",
        "hidden_gem_band",
        "evidence_status",
    ]
    write_csv(OUTPUT_MAIN, output_rows, fields)
    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "built_at"])

    print("EDGEiQ Hidden Gem Engine V1 built")
    print(f"Historical rows processed: {len(output_rows)}")
    print(f"Hidden gem signals: {len(signal_rows)}")
    print(f"Current active watch runners: {len(active_watch_keys)}")
    print(f"Readiness: {summary_row['readiness_verdict']}")


if __name__ == "__main__":
    main()
