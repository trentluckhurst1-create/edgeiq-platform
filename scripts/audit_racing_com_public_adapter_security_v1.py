from __future__ import annotations

import re
import sys

from edgeiq_racing_com_public_common_v1 import *

FORBIDDEN = [
    ("cookie_header", r"Cookie\s*:"),
    ("authorization_header", r"Authorization\s*:"),
    ("bearer_value", r"Bearer\s+[A-Za-z0-9_\-.]+"),
    ("racingcom_key_value", r"da2-[a-z0-9]{10,}"),
    ("endpoint_key_assignment", r"EndpointKey\s*[:=]\s*[\"'][^\"']+[\"']"),
    ("champion_endpoint_key_assignment", r"ChampionDataEndpointKey\s*[:=]\s*[\"'][^\"']+[\"']"),
]
SCRIPT_NAMES = {
    "edgeiq_racing_com_public_common_v1.py",
    "edgeiq_racing_com_public_adapter_v1.py",
    "replay_racing_com_public_graphql_v1.py",
    "replay_racing_com_runner_sectionals_v1.py",
    "import_racing_com_runner_sectionals_official_file_v1.py",
    "investigate_racing_com_frontend_public_data_v1.py",
    "analyse_racing_com_har_v1.py",
    "probe_racing_com_public_sectional_resources_v1.py",
    "run_edgeiq_racing_com_public_acceptance_v1.py",
    "audit_edgeiq_racing_com_public_data_v1.py",
    "build_edgeiq_racing_com_runner_sectionals_completion_v1.py",
    "run_edgeiq_racing_com_visible_sectionals_pipeline_v1.py",
    "import_racing_com_visible_sectionals_v1.py",
    "normalise_racing_com_visible_sectionals_v1.py",
    "edgeiq_racing_com_visible_page_collector_v1.py",
}
ALLOW_FILES = {"audit_racing_com_public_adapter_security_v1.py"}


def iter_files():
    for name in SCRIPT_NAMES | ALLOW_FILES:
        path = ROOT / "scripts" / name
        if path.exists():
            yield path
    for path in DOC.rglob("*"):
        if not path.is_file():
            continue
        if "audit" in path.parts:
            continue
        if path.suffix.lower() in {".py", ".md", ".json", ".txt", ".csv", ".graphql", ".js", ".html"}:
            yield path


def main() -> int:
    ensure()
    rows = []
    failures = 0
    for path in iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in FORBIDDEN:
            matched = bool(re.search(pattern, text, re.I))
            fail = matched and path.name not in ALLOW_FILES
            failures += 1 if fail else 0
            rows.append({"file": str(path.relative_to(ROOT)), "check": name, "matched": "YES" if matched else "NO", "status": "FAIL" if fail else "PASS"})

    visible_forbidden = [
        ("visible_protected_graphql_endpoint", r"graphql\.rmdprod\.racing\.com"),
        ("visible_sectionaltimes_callback", r"sectionaltimes_callback"),
        ("visible_x_api_key_header", r"[\"']x-api-key[\"']\s*:"),
        ("visible_storage_state", r"storage_state"),
        ("visible_cookie_read", r"\.cookies\s*\("),
        ("visible_local_storage", r"localStorage"),
        ("visible_session_storage", r"sessionStorage"),
        ("visible_proxy_evasion", r"proxy\s*=|proxy rotation|captcha|stealth"),
    ]
    visible_scripts = {
        "edgeiq_racing_com_visible_page_collector_v1.py",
        "normalise_racing_com_visible_sectionals_v1.py",
        "import_racing_com_visible_sectionals_v1.py",
        "run_edgeiq_racing_com_visible_sectionals_pipeline_v1.py",
    }
    for name in visible_scripts:
        path = ROOT / "scripts" / name
        if not path.exists():
            failures += 1
            rows.append({"file": str(path.relative_to(ROOT)), "check": "visible_script_exists", "matched": "NO", "status": "FAIL"})
            continue
        visible_text = path.read_text(encoding="utf-8", errors="ignore")
        for check, pattern in visible_forbidden:
            matched = bool(re.search(pattern, visible_text, re.I))
            failures += 1 if matched else 0
            rows.append({"file": str(path.relative_to(ROOT)), "check": check, "matched": "YES" if matched else "NO", "status": "FAIL" if matched else "PASS"})
    verdict = "PASS" if failures == 0 else "FAIL"
    write_csv(AUDIT / "public_adapter_security_v1.csv", rows)
    write_json(AUDIT / "public_adapter_security_v1.json", {"verdict": verdict, "failures": failures})
    print(verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
