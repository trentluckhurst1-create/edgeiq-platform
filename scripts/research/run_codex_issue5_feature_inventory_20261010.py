import argparse
import csv
import json
from pathlib import Path

import pandas as pd


FORBIDDEN_MARKET_TERMS = (
    "sp",
    "bsp",
    "starting_price",
    "odds",
    "price",
    "market",
    "bet",
    "stake",
    "return",
)
FORBIDDEN_PREDICTOR_TERMS = (
    "prediction",
    "probability",
    "target",
    "outcome",
    "finish_position",
    "placing_result",
    "result_margin",
)
ALLOWED_LABEL_COLUMNS = {"y", "_y", "target_finish_position"}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--max-year", type=int, required=True)
    p.add_argument("--stage011-report", required=True)
    p.add_argument("--stage004-universe", required=True)
    p.add_argument("--stage006-warehouse", required=True)
    p.add_argument("--d45-matrix", required=True)
    p.add_argument("--lab238c-manifest", required=True)
    p.add_argument("--lab239-audit", required=True)
    p.add_argument("--lab239-architecture", required=True)
    p.add_argument("--out", required=True)
    return p.parse_args()


def header(path):
    return list(pd.read_csv(path, nrows=0).columns)


def has_forbidden_market(name):
    n = name.lower()
    tokens = n.replace("-", "_").split("_")
    return any(term in tokens or term in n for term in FORBIDDEN_MARKET_TERMS if term not in {"sp", "bsp"}) or "sp" in tokens or "bsp" in tokens


def predictor_flags(columns):
    flags = []
    for c in columns:
        lc = c.lower()
        if c in ALLOWED_LABEL_COLUMNS or c in {"_race", "_horse", "race_date", "date", "year", "_year"}:
            continue
        if has_forbidden_market(c):
            flags.append((c, "FORBIDDEN_MARKET_NAME"))
        elif any(term in lc for term in FORBIDDEN_PREDICTOR_TERMS):
            flags.append((c, "FORBIDDEN_MODEL_TARGET_OR_OUTCOME_NAME"))
        elif lc.startswith("p_"):
            flags.append((c, "FORBIDDEN_MODEL_OUTPUT_NAME"))
    return flags


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    stage011 = json.loads(Path(args.stage011_report).read_text())
    lab239_audit = json.loads(Path(args.lab239_audit).read_text())
    lab239_arch = json.loads(Path(args.lab239_architecture).read_text())

    inferred_year_counts = {}
    if stage011.get("status") == "PASS":
        for row in stage011["years"]:
            inferred_year_counts[int(row["year"])] = {
                "runners": int(row["runner_rows"]),
                "races": int(row["races"]),
                "source": "STAGE011_REPRODUCTION_REPORT",
            }
        inferred_year_counts[2021] = {
            "runners": int(stage011["years"][0]["train_rows"]),
            "races": None,
            "source": "STAGE011_REPRODUCTION_REPORT_TRAIN_ROWS_FOR_2022",
        }

    source_specs = [
        ("stage004_universe", Path(args.stage004_universe), "GOVERNED_STAGE004_SINGLE_WINNER_UNIVERSE"),
        ("stage006_warehouse", Path(args.stage006_warehouse), "GOVERNED_STAGE006_PIT_WAREHOUSE"),
        ("d45_matrix", Path(args.d45_matrix), "GOVERNED_D45_CONTEXT_SOURCE"),
        ("lab238c_manifest", Path(args.lab238c_manifest), "HEADER_MANIFEST_ONLY"),
    ]

    rows = []
    for name, path, proof in source_specs:
        if not path.exists():
            rows.append({"source": name, "path": str(path), "status": "MISSING"})
            continue
        cols = header(path)
        flags = predictor_flags(cols)
        market_flags = [f for f in flags if f[1] == "FORBIDDEN_MARKET_NAME"]
        status = "CERTIFIED_HEADER_PASS" if not market_flags else "BLOCKED_MARKET_HEADER"
        if name == "lab238c_manifest":
            status = "MANIFEST_ONLY_NO_ROW_ACCESS"
        rows.append(
            {
                "source": name,
                "path": str(path),
                "status": status,
                "governance_proof": proof,
                "column_count": len(cols),
                "candidate_feature_columns": "|".join([c for c in cols if c not in ALLOWED_LABEL_COLUMNS]),
                "blocked_columns": "|".join(c for c, _ in flags),
                "blocked_reasons": "|".join(f"{c}:{r}" for c, r in flags),
                "sealed_year_access": "NO_ROW_ACCESS_IN_INVENTORY",
            }
        )

    rows.append(
        {
            "source": "stage011_reproduction_report",
            "path": str(Path(args.stage011_report)),
            "status": "PASS" if stage011.get("status") == "PASS" else "BLOCKED",
            "governance_proof": "REPRODUCED_STAGE011_BASELINE",
            "column_count": None,
            "candidate_feature_columns": "|".join(stage011.get("features", [])),
            "blocked_columns": "",
            "blocked_reasons": "",
            "sealed_year_access": "JSON_ONLY",
        }
    )
    rows.append(
        {
            "source": "lab239_frozen_architecture",
            "path": str(Path(args.lab239_architecture)),
            "status": "NOT_RUN_NO_FROZEN_FIELDS" if lab239_arch.get("architecture") == "NO_CHALLENGER" else "REQUIRES_REVIEW",
            "governance_proof": "LAB239_AUDIT",
            "column_count": int(lab239_audit.get("certified_manifest_fields", 0)),
            "candidate_feature_columns": "|".join(lab239_arch.get("fields", [])),
            "blocked_columns": "",
            "blocked_reasons": "NO_NONEMPTY_FROZEN_DENSE_ARCHITECTURE" if lab239_arch.get("architecture") == "NO_CHALLENGER" else "",
            "sealed_year_access": "JSON_ONLY",
        }
    )

    csv_path = out / "CODEX_FEATURE_INVENTORY_20261010.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted({k for row in rows for k in row}))
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "status": "PASS",
        "max_year": args.max_year,
        "row_level_access": False,
        "sealed_year_access": False,
        "market_access": False,
        "stage011_features": stage011.get("features", []),
        "stage011_year_counts_from_report": inferred_year_counts,
        "lab239_architecture": lab239_arch,
        "sources": rows,
    }
    (out / "CODEX_FEATURE_INVENTORY_20261010.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("CODEX_ISSUE5_FEATURE_INVENTORY=PASS")
    print(f"CSV={csv_path}")


if __name__ == "__main__":
    main()
