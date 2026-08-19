from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = {
    "\u00e2\u2020\u2019": "->",
    "\u00e2\u2020\u0090": "<-",
    "\u00e2\u20ac\u00b9": "<",
    "\u00e2\u20ac\u00ba": ">",
    "\u00c2\u00b7": " / ",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u009d": '"',
}

TARGET_FILES = [
    "src/screens/HomeScreen.tsx",
    "src/screens/MeetingsScreen.tsx",
    "src/services/productShellMeetingService.ts",
    "src/services/commandWorkspaceSummaryService.ts",
    "src/edgeiq-os/race/services/meetingDetailFeed.ts",
    "src/edgeiq-os/race/services/scratchingsFeed.ts",
]


def repair_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)

    lines = text.splitlines()
    fixed = []
    for line in lines:
        stripped = line.strip()
        if path.name in {"meetingDetailFeed.ts", "scratchingsFeed.ts"} and stripped.startswith(
            'if (!text || text === "-"'
        ):
            fixed.append('  if (!text || text === "-" || text === "\\u2014") return "";')
            continue
        if path.name == "productShellMeetingService.ts" and stripped.startswith(
            "const raw = text(value).replace(/"
        ):
            fixed.append('    const raw = text(value).replace(/[\\u2013\\u2014]/g, "-").trim();')
            continue
        if path.name == "commandWorkspaceSummaryService.ts" and stripped.startswith("const cleanWeight ="):
            fixed.append(
                ' const cleanWeight = (row: Row) => firstText(row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"], "-");'
            )
            continue
        fixed.append(line)

    text = "\n".join(fixed) + ("\n" if original.endswith("\n") else "")
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = []
    for rel in TARGET_FILES:
        path = ROOT / rel
        if path.exists() and repair_file(path):
            changed.append(rel)

    out_dir = ROOT / "docs" / "full-product-implementation" / "screenshots" / "approved-ui-rebuild"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "EDGEIQ_ACTIVE_SOURCE_ENCODING_FINAL_REPAIR_V1.txt"
    report.write_text(
        "EDGEIQ_ACTIVE_SOURCE_ENCODING_FINAL_REPAIR_V1\n"
        f"changed_files={len(changed)}\n"
        + "\n".join(changed)
        + ("\n" if changed else ""),
        encoding="utf-8",
    )
    print(f"changed_files={len(changed)}")
    for rel in changed:
        print(rel)


if __name__ == "__main__":
    main()
