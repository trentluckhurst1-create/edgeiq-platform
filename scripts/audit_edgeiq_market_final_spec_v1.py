from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MarketWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "marketFeed.ts"
FEED = ROOT / "public" / "data" / "edgeiq_market_terminal_feed_v1.csv"
DOC = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MARKET_FINAL_SPEC_AUDIT_V1.md"
CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_market_final_spec_audit_v1.csv"


def read(path: Path) -> str:
  return path.read_text(encoding="utf-8")


def check(name: str, passed: bool, detail: str) -> dict[str, str]:
  return {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def feed_rows() -> list[dict[str, str]]:
  with FEED.open(encoding="utf-8-sig", newline="") as handle:
    return list(csv.DictReader(handle))


def main() -> None:
  component = read(COMPONENT)
  service = read(SERVICE)
  rows = feed_rows() if FEED.exists() else []
  component_lower = component.lower()
  prohibited = [
    "exchange ladder",
    "betting button",
    "stake control",
    "place-bet",
    "place bet",
    "predicted return",
    "confidence",
  ]

  required_headers = ["NO", "RUNNER", "EDGEIQ", "MARKET", "FAIR", "EDGE", "FLUC 60s %", "STATUS"]
  checks = [
    check(
      "COLUMN_SET_LOCKED",
      all(f"<th>{header}</th>" in component for header in required_headers),
      "MARKET table uses the locked eight-column set.",
    ),
    check(
      "NO_PROHIBITED_MARKET_COPY",
      not any(term in component_lower for term in prohibited),
      "Component has no betting controls, exchange ladder, predicted-return or confidence language.",
    ),
    check(
      "EDGE_FROM_FEED_ONLY",
      "edge: firstText(row.edge)" in service and "edgeiq_price: firstText(row.edgeiq_price)" in service,
      "EDGE and FAIR values are read from the terminal feed rather than calculated in React.",
    ),
    check(
      "FLUC_FROM_FEED_ONLY",
      "move: firstText(row.move)" in service and "FLUC 60s %" in component,
      "FLUC 60s % displays the governed move field.",
    ),
    check(
      "PENDING_MARKET_STATE",
      "Pending Market" in component and "pending_market" in service,
      "Unavailable prices render as Pending Market rather than fake values.",
    ),
    check(
      "FRONTEND_FEED_SIZE_SAFE",
      len(rows) <= 10000,
      f"Market terminal feed rows: {len(rows)}.",
    ),
  ]

  CSV.parent.mkdir(parents=True, exist_ok=True)
  with CSV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
    writer.writeheader()
    writer.writerows(checks)

  DOC.write_text(
    "# EDGEiQ MARKET Final Spec Audit V1\n\n"
    + "\n".join(f"- {row['status']}: {row['check']} - {row['detail']}" for row in checks)
    + "\n",
    encoding="utf-8",
  )

  failures = [row for row in checks if row["status"] != "PASS"]
  if failures:
    print("EDGEIQ_MARKET_FINAL_SPEC_AUDIT_FAIL")
    for failure in failures:
      print(f"{failure['check']}: {failure['detail']}")
    raise SystemExit(1)

  print("EDGEIQ_MARKET_FINAL_SPEC_AUDIT_PASS")


if __name__ == "__main__":
  main()
