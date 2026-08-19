from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
)

BRIDGE = (
    ROOT
    / "scripts"
    / "lab"
    / "edgeiq_lab_a21e1_bridge_v1.py"
)


def run_bridge(
    args: list[str],
) -> subprocess.CompletedProcess[str]:

    env = os.environ.copy()

    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(BRIDGE),
            *args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def require(
    condition: bool,
    message: str,
) -> None:

    if not condition:
        raise RuntimeError(
            message
        )


print(
    "=" * 78
)

print(
    "EDGEIQ LAB A21E1 BRIDGE V1 — CONTRACT TEST"
)

print(
    "=" * 78
)


# ---------------------------------------------------------------------
# TEST 1 — describe
# ---------------------------------------------------------------------

describe = run_bridge(
    ["--describe"]
)

require(
    describe.returncode == 0,
    "DESCRIBE failed:\n"
    + describe.stderr,
)

metadata = json.loads(
    describe.stdout
)

require(
    metadata["status"]
    == "PASS",
    "DESCRIBE status failed.",
)

require(
    metadata[
        "contract_version"
    ]
    == "edgeiq.lab.a21e1.v1",
    "Unexpected contract version.",
)

filterable = metadata[
    "catalog"
][
    "filterable_fields"
]

filterable_names = {
    str(
        row.get(
            "normalized_column"
        )
        or row.get(
            "column"
        )
        or ""
    ).strip().lower()
    for row in filterable
}

require(
    "epi_mean_last3_top1"
    in filterable_names,
    "Governed EPI top1 filter "
    "missing from catalog.",
)

print(
    "DESCRIBE=PASS"
)

print(
    "FILTERABLE_FIELDS="
    + str(
        metadata[
            "catalog"
        ][
            "filterable_count"
        ]
    )
)

print(
    "FIELD_ROLES="
    + str(
        metadata[
            "catalog"
        ][
            "field_role_count"
        ]
    )
)


# ---------------------------------------------------------------------
# TEST 2 — forbidden SP filter must fail before governed run
# ---------------------------------------------------------------------

with tempfile.TemporaryDirectory(
    prefix="edgeiq_lab_test_"
) as temp_name:

    temp = Path(
        temp_name
    )

    forbidden_path = (
        temp
        / "forbidden.json"
    )

    forbidden_path.write_text(
        json.dumps(
            {
                "name":
                    "Forbidden SP Filter Test",

                "splits":
                    ["TRAIN"],

                "filters": [
                    {
                        "field":
                            "starting_price",

                        "operator":
                            "gte",

                        "value":
                            2,
                    }
                ],

                "breakdowns":
                    [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    forbidden = run_bridge(
        [
            str(
                forbidden_path
            )
        ]
    )

    require(
        forbidden.returncode != 0,
        "Forbidden starting_price "
        "filter unexpectedly passed.",
    )

    forbidden_error = forbidden.stderr.lower()

    require(
        "starting_price"
        in forbidden_error,
        "Forbidden-filter rejection "
        "did not identify starting_price.\n"
        + forbidden.stderr,
    )

    require(
        (
            "not permitted"
            in forbidden_error
            or
            "not present in the governed a21e1 catalog"
            in forbidden_error
        ),
        "Forbidden-filter rejection "
        "did not come from governed "
        "catalog pre-validation.\n"
        + forbidden.stderr,
    )

print(
    "FORBIDDEN_SP_FILTER=PASS"
)


# ---------------------------------------------------------------------
# TEST 3 — genuine governed analysis
# ---------------------------------------------------------------------

with tempfile.TemporaryDirectory(
    prefix="edgeiq_lab_test_"
) as temp_name:

    temp = Path(
        temp_name
    )

    request_path = (
        temp
        / "request.json"
    )

    request = {
        "query": {
            "name":
                "LAB Hardened Bridge Test",

            "splits":
                ["TRAIN"],

            "filters": [
                {
                    "field":
                        "epi_mean_last3_top1",

                    "operator":
                        "eq",

                    "value":
                        1,
                },
                {
                    "field":
                        "epi_mean_last3_minus_field_mean",

                    "operator":
                        "gte",

                    "value":
                        0,
                },
            ],

            "breakdowns": [
                "year",
                "canonical_track",
            ],
        },

        "options": {
            "qualifying_runner_limit":
                25,

            "include_catalog":
                False,

            "include_field_roles":
                False,
        },
    }

    request_path.write_text(
        json.dumps(
            request,
            indent=2,
        ),
        encoding="utf-8",
    )

    governed = run_bridge(
        [
            str(
                request_path
            )
        ]
    )

    require(
        governed.returncode == 0,
        "Governed analysis failed:\n"
        + governed.stderr,
    )

    result = json.loads(
        governed.stdout
    )

    require(
        result["status"]
        == "PASS",
        "Governed status "
        "was not PASS.",
    )

    require(
        result["engine"]["id"]
        == "A21E1",
        "Unexpected engine.",
    )

    governance = result[
        "governance"
    ]

    require(
        governance[
            "verdict"
        ]
        ==
        "PASS_GOVERNED_USER_ANALYSIS_ENGINE_V1",
        "Governance verdict failed.",
    )

    require(
        str(
            governance[
                "final_holdout_rows_seen"
            ]
        )
        == "0",
        "Final holdout exposure "
        "was not zero.",
    )

    require(
        governance[
            "hard_failures"
        ]
        == "NONE",
        "Hard failures were reported.",
    )

    qualifiers = result[
        "qualifying_runners"
    ]

    require(
        qualifiers[
            "returned"
        ]
        <= 25,
        "Qualifier preview "
        "limit failed.",
    )

    require(
        qualifiers[
            "total"
        ]
        >= qualifiers[
            "returned"
        ],
        "Qualifier total "
        "contract failed.",
    )

    overall = (
        result[
            "overall"
        ][0]
        if result[
            "overall"
        ]
        else {}
    )

    print(
        "GOVERNED_ANALYSIS=PASS"
    )

    print(
        "WAREHOUSE_SHA256="
        + str(
            governance[
                "warehouse_sha256"
            ]
        )
    )

    print(
        "WAREHOUSE_ROWS_READ="
        + str(
            governance[
                "warehouse_rows_read"
            ]
        )
    )

    print(
        "FINAL_HOLDOUT_ROWS_SEEN="
        + str(
            governance[
                "final_holdout_rows_seen"
            ]
        )
    )

    print(
        "HARD_FAILURES="
        + str(
            governance[
                "hard_failures"
            ]
        )
    )

    print(
        "QUALIFYING_TOTAL="
        + str(
            qualifiers[
                "total"
            ]
        )
    )

    print(
        "QUALIFYING_RETURNED="
        + str(
            qualifiers[
                "returned"
            ]
        )
    )

    print(
        "BETS="
        + str(
            overall.get(
                "bets",
                ""
            )
        )
    )

    print(
        "WINS="
        + str(
            overall.get(
                "wins",
                ""
            )
        )
    )

    print(
        "STRIKE_RATE_PCT="
        + str(
            overall.get(
                "win_strike_rate_pct",
                ""
            )
        )
    )

    print(
        "ROI_PCT="
        + str(
            overall.get(
                "roi_pct",
                ""
            )
        )
    )


print(
    "=" * 78
)

print(
    "EDGEIQ_LAB_BACKEND_CONTRACT=PASS"
)

print(
    "=" * 78
)
