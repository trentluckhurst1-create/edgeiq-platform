from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS_FILE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

OLD = """.eiq-map-v1-runner-line.is-unavailable .eiq-map-v1-runner-line__label {
  margin-left: 70%;
  opacity: 0.78;
}
"""

NEW = """.eiq-map-v1-runner-line.is-unavailable .eiq-map-v1-runner-line__label {
  width: min(230px, 30%);
  max-width: min(230px, 30%);
  min-width: 168px;
  margin-left: 68%;
  opacity: 0.78;
}
"""


def main() -> None:
  source = CSS_FILE.read_text(encoding="utf-8")
  if NEW in source:
    print("EDGEIQ_MAP_UNAVAILABLE_LABEL_WIDTH_ALREADY_APPLIED")
    return
  if OLD not in source:
    raise RuntimeError("Could not find unavailable MAP label width target")
  CSS_FILE.write_text(source.replace(OLD, NEW, 1), encoding="utf-8")
  print("EDGEIQ_MAP_UNAVAILABLE_LABEL_WIDTH_APPLIED")


if __name__ == "__main__":
  main()
