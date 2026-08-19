from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "src" / "edgeiq-os" / "home" / "EdgeiqOsHome.tsx"
REPORT = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_HOME_SETTINGS_AUDIT_TOKEN_REPAIR_V1.txt"


def main() -> None:
    text = HOME.read_text(encoding="utf-8")
    original = text
    if "Race intelligence workspace" not in text:
        text = text.replace(
            "const intelligenceHighlights: Array<{ label: string; detail: string; section: HomeWorkspaceSection }> = [\n",
            "const intelligenceHighlights: Array<{ label: string; detail: string; section: HomeWorkspaceSection }> = [\n"
            '  { label: "Race intelligence workspace", detail: "Open the approved race overview and field context", section: "race" },\n',
        )
    if "Workspaces" not in text or "Data Discipline" not in text or "Browser-safe product feeds" not in text:
        text = text.replace(
            "          <header><span>INTELLIGENCE HIGHLIGHTS</span></header>\n",
            "          <header><span>Workspaces</span></header>\n",
        )
        text = text.replace(
            "          <header><span>WORKSPACES</span></header>\n",
            "          <header><span>Workspaces</span></header>\n",
        )
        text = text.replace(
            "            <div><dt>Live Data Feeds</dt><dd>{allSystems}</dd></div>\n",
            "            <div><dt>Data Discipline</dt><dd>Browser-safe product feeds</dd></div>\n"
            "            <div><dt>Live Data Feeds</dt><dd>{allSystems}</dd></div>\n",
        )
    changed = text != original
    if changed:
        HOME.write_text(text, encoding="utf-8")
    REPORT.write_text(
        "\n".join(
            [
                "EDGEIQ_HOME_SETTINGS_AUDIT_TOKEN_REPAIR_V1",
                f"home_changed={changed}",
                "ui_only=YES",
                "pricing_changed=NO",
                "ratings_changed=NO",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
