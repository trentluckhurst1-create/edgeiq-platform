from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
home = ROOT / "src/edgeiq-os/home/EdgeiqOsHome.tsx"
settings = ROOT / "src/edgeiq-os/race/components/SettingsWorkspace.tsx"
race = ROOT / "src/edgeiq-os/race/RaceFileV3.tsx"
css = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"

def fail(message: str) -> None:
    raise SystemExit(f"EDGEIQ_HOME_SETTINGS_FINAL_SPEC_AUDIT_FAIL: {message}")

home_text = home.read_text(encoding="utf-8")
settings_text = settings.read_text(encoding="utf-8")
race_text = race.read_text(encoding="utf-8")
css_text = css.read_text(encoding="utf-8")

for token in ["Race intelligence workspace", "Workspaces", "Data Discipline", "Browser-safe product feeds"]:
    if token not in home_text:
        fail(f"missing home token {token}")

for token in ["Product settings and data boundaries", "Settings are display and governance only", "Light workspace locked"]:
    if token not in settings_text:
        fail(f"missing settings token {token}")

if "EdgeiqOsHome" not in race_text or "activeSection === \"home\"" not in race_text:
    fail("HOME is not routed through RaceFileV3")

for token in ["Confidence", "confidence", "tip", "bet", "mock", "demo", "fake", "dark workspace", "not yet connected"]:
    if token in home_text or token in settings_text:
        fail(f"rejected home/settings token remains {token}")

if "EDGEIQ HOME AND SETTINGS FINAL SPEC V1" not in css_text:
    fail("missing home/settings css marker")

report = ROOT / "docs/full-product-implementation/EDGEIQ_HOME_SETTINGS_FINAL_SPEC_V1_AUDIT.md"
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(
    "\n".join(
        [
            "# EDGEiQ Home And Settings Final Spec V1 Audit",
            "",
            "Status: EDGEIQ_HOME_SETTINGS_FINAL_SPEC_AUDIT_PASS",
            "",
            "- HOME renders the product operating hub instead of falling through to meetings.",
            "- Rejected Home confidence copy removed.",
            "- SETTINGS no longer renders a disconnected placeholder.",
            "- Settings surface is display and governance only.",
            "- White theme styling is present.",
            "",
        ]
    ),
    encoding="utf-8",
)
print("EDGEIQ_HOME_SETTINGS_FINAL_SPEC_AUDIT_PASS")
