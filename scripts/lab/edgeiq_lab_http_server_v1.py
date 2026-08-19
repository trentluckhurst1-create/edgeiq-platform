from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


HOST = "127.0.0.1"
PORT = 8765

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
) -> tuple[int, str, str]:

    env = os.environ.copy()

    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.run(
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

    return (
        process.returncode,
        process.stdout,
        process.stderr,
    )


class LabHandler(BaseHTTPRequestHandler):

    server_version = "EDGEiQLabHTTP/1.0"

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:

        sys.stdout.write(
            "LAB_HTTP "
            + (format % args)
            + "\n"
        )

    def send_json(
        self,
        status_code: int,
        payload: dict[str, Any],
    ) -> None:

        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def read_json_body(
        self,
    ) -> dict[str, Any]:

        raw_length = self.headers.get(
            "Content-Length",
            "0",
        )

        try:
            length = int(
                raw_length
            )
        except ValueError as exc:
            raise RuntimeError(
                "Invalid Content-Length."
            ) from exc

        if length <= 0:
            raise RuntimeError(
                "Request body is required."
            )

        raw = self.rfile.read(
            length
        )

        try:
            payload = json.loads(
                raw.decode("utf-8")
            )
        except Exception as exc:
            raise RuntimeError(
                "Request body must be valid UTF-8 JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                "Request JSON must be an object."
            )

        return payload

    def do_OPTIONS(
        self,
    ) -> None:

        self.send_response(
            204
        )

        self.send_header(
            "Allow",
            "GET, POST, OPTIONS",
        )

        self.send_header(
            "Content-Length",
            "0",
        )

        self.end_headers()

    def do_GET(
        self,
    ) -> None:

        if self.path == "/api/lab/health":

            self.send_json(
                200,
                {
                    "status": "PASS",
                    "service": "EDGEIQ_LAB_HTTP_V1",
                    "bridge_exists": BRIDGE.is_file(),
                },
            )

            return

        if self.path == "/api/lab/describe":

            exit_code, stdout, stderr = (
                run_bridge(
                    ["--describe"]
                )
            )

            if exit_code != 0:

                self.send_json(
                    500,
                    {
                        "status": "ERROR",
                        "error": (
                            stderr.strip()
                            or stdout.strip()
                            or
                            "LAB describe failed."
                        ),
                    },
                )

                return

            try:
                payload = json.loads(
                    stdout
                )
            except Exception as exc:

                self.send_json(
                    500,
                    {
                        "status": "ERROR",
                        "error": (
                            "LAB describe returned "
                            "invalid JSON: "
                            + str(exc)
                        ),
                    },
                )

                return

            self.send_json(
                200,
                payload,
            )

            return

        self.send_json(
            404,
            {
                "status": "ERROR",
                "error": "Not found.",
            },
        )

    def do_POST(
        self,
    ) -> None:

        if self.path != "/api/lab/run":

            self.send_json(
                404,
                {
                    "status": "ERROR",
                    "error": "Not found.",
                },
            )

            return

        try:
            payload = self.read_json_body()

            with tempfile.TemporaryDirectory(
                prefix="edgeiq_lab_http_"
            ) as temp_name:

                request_path = (
                    Path(temp_name)
                    / "request.json"
                )

                request_path.write_text(
                    json.dumps(
                        payload,
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                exit_code, stdout, stderr = (
                    run_bridge(
                        [
                            str(
                                request_path
                            )
                        ]
                    )
                )

            if exit_code != 0:

                message = (
                    stderr.strip()
                    or stdout.strip()
                    or
                    "LAB analysis failed."
                )

                try:
                    error_payload = json.loads(
                        message
                    )

                    if not isinstance(
                        error_payload,
                        dict,
                    ):
                        raise ValueError()

                except Exception:
                    error_payload = {
                        "status": "ERROR",
                        "error": message,
                    }

                self.send_json(
                    400,
                    error_payload,
                )

                return

            try:
                result = json.loads(
                    stdout
                )
            except Exception as exc:

                self.send_json(
                    500,
                    {
                        "status": "ERROR",
                        "error": (
                            "LAB analysis returned "
                            "invalid JSON: "
                            + str(exc)
                        ),
                    },
                )

                return

            self.send_json(
                200,
                result,
            )

        except Exception as exc:

            self.send_json(
                400,
                {
                    "status": "ERROR",
                    "error": str(exc),
                },
            )


def main() -> int:

    if not BRIDGE.is_file():
        raise RuntimeError(
            f"LAB bridge not found: {BRIDGE}"
        )

    print(
        "=" * 78
    )

    print(
        "EDGEIQ LAB HTTP SERVER V1"
    )

    print(
        f"HOST={HOST}"
    )

    print(
        f"PORT={PORT}"
    )

    print(
        f"HEALTH=http://{HOST}:{PORT}/api/lab/health"
    )

    print(
        f"DESCRIBE=http://{HOST}:{PORT}/api/lab/describe"
    )

    print(
        f"RUN=http://{HOST}:{PORT}/api/lab/run"
    )

    print(
        "=" * 78
    )

    server = ThreadingHTTPServer(
        (HOST, PORT),
        LabHandler,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
