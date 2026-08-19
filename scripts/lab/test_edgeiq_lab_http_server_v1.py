from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
)

SERVER = (
    ROOT
    / "scripts"
    / "lab"
    / "edgeiq_lab_http_server_v1.py"
)

BASE = "http://127.0.0.1:8765"


def request_json(
    method: str,
    path: str,
    payload: dict | None = None,
) -> tuple[int, dict]:

    data = None

    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(
            payload
        ).encode("utf-8")

        headers[
            "Content-Type"
        ] = "application/json"

    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=300,
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

            return (
                response.status,
                json.loads(raw),
            )

    except urllib.error.HTTPError as exc:

        raw = exc.read().decode(
            "utf-8"
        )

        return (
            exc.code,
            json.loads(raw),
        )


def require(
    condition: bool,
    message: str,
) -> None:

    if not condition:
        raise RuntimeError(
            message
        )


env = os.environ.copy()

env["PYTHONUTF8"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

server = subprocess.Popen(
    [
        sys.executable,
        "-X",
        "utf8",
        str(SERVER),
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=env,
)


try:

    ready = False

    for _ in range(40):

        time.sleep(
            0.25
        )

        try:
            status, health = request_json(
                "GET",
                "/api/lab/health",
            )

            if (
                status == 200
                and
                health.get("status")
                == "PASS"
            ):
                ready = True
                break

        except Exception:
            pass

    require(
        ready,
        "LAB HTTP server did not become ready.",
    )

    print(
        "HTTP_HEALTH=PASS"
    )

    status, describe = request_json(
        "GET",
        "/api/lab/describe",
    )

    require(
        status == 200,
        "Describe HTTP status failed.",
    )

    require(
        describe.get("status")
        == "PASS",
        "Describe payload failed.",
    )

    require(
        describe.get(
            "contract_version"
        )
        == "edgeiq.lab.a21e1.v1",
        "Describe contract mismatch.",
    )

    print(
        "HTTP_DESCRIBE=PASS"
    )

    status, forbidden = request_json(
        "POST",
        "/api/lab/run",
        {
            "name":
                "Forbidden HTTP SP Test",

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
    )

    require(
        status == 400,
        "Forbidden HTTP filter "
        "did not return 400.",
    )

    require(
        forbidden.get("status")
        == "ERROR",
        "Forbidden HTTP payload "
        "did not fail.",
    )

    print(
        "HTTP_FORBIDDEN_FILTER=PASS"
    )

    print(
        "=" * 78
    )

    print(
        "EDGEIQ_LAB_HTTP_CONTRACT=PASS"
    )

    print(
        "=" * 78
    )


finally:

    server.terminate()

    try:
        server.wait(
            timeout=5
        )
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
