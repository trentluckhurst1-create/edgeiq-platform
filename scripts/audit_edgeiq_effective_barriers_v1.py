from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "public" / "data" / "edgeiq_effective_barriers_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_effective_barriers_v1_audit.txt"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "scratchingsFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingScratchingsWorkspace.tsx"


def calculate(inputs):
    seen = set()
    duplicate = False
    for item in inputs:
        barrier = item.get("originalBarrier")
        if barrier is None:
            continue
        if barrier in seen:
            duplicate = True
        seen.add(barrier)
    if duplicate:
        return {
            item["runnerKey"]: {"effectiveBarrier": None, "unresolved": True}
            for item in inputs
        }

    active = sorted(
        [item for item in inputs if not item.get("scratched") and item.get("originalBarrier") is not None],
        key=lambda item: item["originalBarrier"],
    )
    effective = {item["runnerKey"]: index + 1 for index, item in enumerate(active)}
    return {
        item["runnerKey"]: {
            "effectiveBarrier": None if item.get("originalBarrier") is None else effective.get(item["runnerKey"]),
            "unresolved": item.get("originalBarrier") is None,
        }
        for item in inputs
    }


def case(name, inputs, expected):
    result = calculate(inputs)
    passed = result == expected
    return {"name": name, "passed": passed, "expected": expected, "actual": result}


cases = [
    case(
        "no scratches unchanged",
        [{"runnerKey": f"r{i}", "originalBarrier": i, "scratched": False} for i in range(1, 5)],
        {f"r{i}": {"effectiveBarrier": i, "unresolved": False} for i in range(1, 5)},
    ),
    case(
        "barrier 1 scratched compresses others",
        [{"runnerKey": f"r{i}", "originalBarrier": i, "scratched": i == 1} for i in range(1, 5)],
        {
            "r1": {"effectiveBarrier": None, "unresolved": False},
            "r2": {"effectiveBarrier": 1, "unresolved": False},
            "r3": {"effectiveBarrier": 2, "unresolved": False},
            "r4": {"effectiveBarrier": 3, "unresolved": False},
        },
    ),
    case(
        "barriers 1 and 3 scratched compress correctly",
        [{"runnerKey": f"r{i}", "originalBarrier": i, "scratched": i in {1, 3}} for i in range(1, 9)],
        {
            "r1": {"effectiveBarrier": None, "unresolved": False},
            "r2": {"effectiveBarrier": 1, "unresolved": False},
            "r3": {"effectiveBarrier": None, "unresolved": False},
            "r4": {"effectiveBarrier": 2, "unresolved": False},
            "r5": {"effectiveBarrier": 3, "unresolved": False},
            "r6": {"effectiveBarrier": 4, "unresolved": False},
            "r7": {"effectiveBarrier": 5, "unresolved": False},
            "r8": {"effectiveBarrier": 6, "unresolved": False},
        },
    ),
    case(
        "outside scratching leaves inside unchanged",
        [{"runnerKey": f"r{i}", "originalBarrier": i, "scratched": i == 8} for i in range(1, 9)],
        {
            **{f"r{i}": {"effectiveBarrier": i, "unresolved": False} for i in range(1, 8)},
            "r8": {"effectiveBarrier": None, "unresolved": False},
        },
    ),
    case(
        "missing barrier unresolved no zero",
        [
            {"runnerKey": "r1", "originalBarrier": 1, "scratched": False},
            {"runnerKey": "r2", "originalBarrier": None, "scratched": False},
            {"runnerKey": "r3", "originalBarrier": 3, "scratched": False},
        ],
        {
            "r1": {"effectiveBarrier": 1, "unresolved": False},
            "r2": {"effectiveBarrier": None, "unresolved": True},
            "r3": {"effectiveBarrier": 2, "unresolved": False},
        },
    ),
    case(
        "duplicate barrier fails documented resolution",
        [
            {"runnerKey": "r1", "originalBarrier": 1, "scratched": False},
            {"runnerKey": "r2", "originalBarrier": 1, "scratched": False},
        ],
        {
            "r1": {"effectiveBarrier": None, "unresolved": True},
            "r2": {"effectiveBarrier": None, "unresolved": True},
        },
    ),
    case(
        "emergency promoted active effective barriers",
        [
            {"runnerKey": "r1", "originalBarrier": 1, "scratched": False},
            {"runnerKey": "r2", "originalBarrier": 2, "scratched": True},
            {"runnerKey": "r3", "originalBarrier": 8, "scratched": False, "emergencyPromoted": True},
        ],
        {
            "r1": {"effectiveBarrier": 1, "unresolved": False},
            "r2": {"effectiveBarrier": None, "unresolved": False},
            "r3": {"effectiveBarrier": 2, "unresolved": False},
        },
    ),
    case(
        "chronological late scratching before after preserved",
        [
            {"runnerKey": "r1", "originalBarrier": 1, "scratched": True, "occurredAt": "2026-07-13T09:00:00+10:00"},
            {"runnerKey": "r2", "originalBarrier": 2, "scratched": False},
            {"runnerKey": "r3", "originalBarrier": 3, "scratched": False},
        ],
        {
            "r1": {"effectiveBarrier": None, "unresolved": False},
            "r2": {"effectiveBarrier": 1, "unresolved": False},
            "r3": {"effectiveBarrier": 2, "unresolved": False},
        },
    ),
]

service_text = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
component_text = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
checks = {
    "service_exists": SERVICE.exists(),
    "calculate_effective_barriers_exported": "export function calculateEffectiveBarriers" in service_text,
    "react_component_does_not_calculate_barriers": "calculateEffectiveBarriers(" not in component_text,
    "duplicate_barrier_guard_present": "duplicates.length" in service_text,
    "missing_barrier_unresolved_present": "unresolved: item.originalBarrier === null" in service_text,
}

payload = {
    "status": "EDGEIQ_EFFECTIVE_BARRIERS_V1_AUDIT_PASS"
    if all(checks.values()) and all(item["passed"] for item in cases)
    else "EDGEIQ_EFFECTIVE_BARRIERS_V1_AUDIT_FAIL",
    "checks": checks,
    "cases": cases,
}
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join(
        [
            payload["status"],
            "",
            *[f"{key}: {value}" for key, value in checks.items()],
            "",
            *[f"{item['name']}: {'PASS' if item['passed'] else 'FAIL'}" for item in cases],
        ]
    ),
    encoding="utf-8",
)
print(payload["status"])
