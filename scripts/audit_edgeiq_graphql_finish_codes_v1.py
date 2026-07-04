from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_graphql_january_2025_results_v1.csv"
OUT = DATA / "edgeiq_graphql_finish_code_audit_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_finish_code_audit_v1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    rows = read_csv(INFILE)

    by_finish = Counter(clean(r.get("finish")) for r in rows)
    samples = defaultdict(list)

    for r in rows:
        f = clean(r.get("finish"))
        if len(samples[f]) < 8:
            samples[f].append(
                f'{clean(r.get("race_date"))} | {clean(r.get("track"))} R{clean(r.get("race_no"))} | '
                f'{clean(r.get("horse"))} | margin={clean(r.get("margin"))} | '
                f'sp={clean(r.get("starting_price"))} | barrier={clean(r.get("barrier"))} | '
                f'scratched={clean(r.get("scratched"))}'
            )

    out_rows = []
    for f, n in sorted(by_finish.items(), key=lambda x: (9999 if x[0] == "" else int(x[0]) if x[0].isdigit() else 9998, x[0])):
        finish_int = int(f) if f.isdigit() else None
        likely_status = "UNKNOWN"
        if finish_int is not None:
            if 1 <= finish_int <= 30:
                likely_status = "FINISHED"
            elif finish_int == 100:
                likely_status = "DID_NOT_FINISH_OR_SPECIAL_CODE_CHECK_REQUIRED"
            elif finish_int == 109:
                likely_status = "SCRATCHED_OR_NON_RUNNER_CHECK_REQUIRED"
            else:
                likely_status = "SPECIAL_CODE_CHECK_REQUIRED"

        out_rows.append({
            "finish_code": f,
            "count": n,
            "likely_status": likely_status,
            "sample_rows": " || ".join(samples[f]),
            "built_at": built_at,
        })

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["finish_code", "count", "likely_status", "sample_rows", "built_at"])
        w.writeheader()
        w.writerows(out_rows)

    summary = [
        {"metric": "status", "value": "EDGEIQ_GRAPHQL_FINISH_CODE_AUDIT_V1_BUILT"},
        {"metric": "input_rows", "value": len(rows)},
        {"metric": "distinct_finish_codes", "value": len(by_finish)},
        {"metric": "finish_109_count", "value": by_finish.get("109", 0)},
        {"metric": "finish_100_count", "value": by_finish.get("100", 0)},
        {"metric": "blank_finish_count", "value": by_finish.get("", 0)},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_FINISH_CODE_AUDIT_V1] COMPLETE")
    print(f"rows={len(out_rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
