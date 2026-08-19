from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "OverviewWorkspace.tsx"


def main() -> None:
    text = COMPONENT.read_text(encoding="utf-8")
    before = text
    text = text.replace("mapRow?.rowStatus", "mapRow?.row_status")
    if text == before:
        raise SystemExit("Expected mapRow?.rowStatus token was not found.")
    COMPONENT.write_text(text, encoding="utf-8")
    print("EDGEIQ_OVERVIEW_MAP_ROW_STATUS_FIX_APPLIED")


if __name__ == "__main__":
    main()
