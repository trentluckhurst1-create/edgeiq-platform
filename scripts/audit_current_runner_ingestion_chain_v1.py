from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "current_runner_ingestion_chain_audit_v1.txt"

TARGET_OUTPUTS = [
    "edgeiq_live_runner_board_governed_v1.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_vic_live_fields_synced.csv",
    "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1.csv",
    "edgeiq_graphql_master_v2.csv",
]

TOKENS = [
    *TARGET_OUTPUTS,
    "GetRacesForMeet",
    "graphql",
    "acceptances",
    "declarations",
    "runner",
    "barrier",
    "jockey",
    "trainer",
    "weight",
    "silk",
]

def context(lines, line_number, before=8, after=12):
    start = max(1, line_number - before)
    end = min(len(lines), line_number + after)
    return [
        f"{index:05d}: {lines[index - 1]}"
        for index in range(start, end + 1)
    ]

matches = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if path.suffix.lower() not in {".py", ".ps1", ".ts", ".tsx", ".js", ".json"}:
        continue

    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        continue

    lines = text.splitlines()
    lower_text = text.lower()

    score = sum(1 for token in TOKENS if token.lower() in lower_text)

    writes_target = any(
        target.lower() in lower_text
        and any(writer in lower_text for writer in [
            "write_csv",
            "to_csv",
            "dictwriter",
            "write_text",
            "copy-item",
            "copyfile",
            "replace(",
        ])
        for target in TARGET_OUTPUTS
    )

    if score < 2 and not writes_target:
        continue

    hits = []

    for index, line in enumerate(lines, start=1):
        lowered = line.lower()

        if any(token.lower() in lowered for token in TOKENS):
            hits.append((index, line))

    matches.append({
        "path": path,
        "score": score,
        "writes_target": writes_target,
        "hits": hits,
        "lines": lines,
    })

matches.sort(
    key=lambda item: (
        not item["writes_target"],
        -item["score"],
        str(item["path"]).lower(),
    )
)

report = []
report.append("EDGEIQ CURRENT RUNNER INGESTION CHAIN AUDIT")
report.append("=" * 120)
report.append("")
report.append("PURPOSE:")
report.append("Identify the true upstream writer and ingestion source for current official runner metadata.")
report.append("")

for item in matches[:60]:
    relative = item["path"].relative_to(ROOT)

    report.append("=" * 120)
    report.append(f"FILE={relative}")
    report.append(f"SCORE={item['score']}")
    report.append(f"WRITES_TARGET={str(item['writes_target']).upper()}")

    shown_ranges = set()

    for line_number, line in item["hits"][:20]:
        range_key = line_number // 15

        if range_key in shown_ranges:
            continue

        shown_ranges.add(range_key)
        report.append("")
        report.append(f"--- Around line {line_number} ---")
        report.extend(context(item["lines"], line_number))

report.append("")
report.append("=" * 120)
report.append("AUDIT_COMPLETE")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print("")
print(f"OUTPUT={OUT}")
print("CURRENT_RUNNER_INGESTION_CHAIN_AUDIT_COMPLETE")
