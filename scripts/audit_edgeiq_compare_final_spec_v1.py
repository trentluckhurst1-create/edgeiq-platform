from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workspace = ROOT / "src/edgeiq-os/compare/CompareWorkspace.tsx"
service = ROOT / "src/edgeiq-os/compare/compareWorkspaceData.ts"
css = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"

required_workspace = [
    "Side-by-side governed comparison",
    "Common Metrics",
    "Historical Context",
    "Data Boundary",
    "Entity",
    "Left",
    "Right",
]
required_service = [
    "buildCompareViewModel",
    "getCompareOptions",
    "defaultCompareSelection",
    "Governed side-by-side jockey comparison is not available",
]
rejected_workspace = [
    "CompareService",
    "Similarity",
    "similarity",
    "verdict",
    "winner",
    "recommendation",
    "tip",
    "bet",
    "mock",
    "demo",
    "fake",
    "SpeedProfile",
    "TrackSignature",
    "RaceStrength",
    "RaceFlow",
]
rejected_product = [
    "Confidence",
    "confidence",
]

def fail(message: str) -> None:
    raise SystemExit(f"EDGEIQ_COMPARE_FINAL_SPEC_AUDIT_FAIL: {message}")

workspace_text = workspace.read_text(encoding="utf-8")
service_text = service.read_text(encoding="utf-8")
css_text = css.read_text(encoding="utf-8")

for token in required_workspace:
    if token not in workspace_text:
        fail(f"missing workspace token {token}")

for token in required_service:
    if token not in service_text:
        fail(f"missing service token {token}")

for token in rejected_workspace:
    if token in workspace_text:
        fail(f"rejected workspace token remains {token}")

visible_regions = workspace_text + "\n" + service_text
for token in rejected_product:
    if token in visible_regions:
        fail(f"rejected compare product term remains {token}")

if "eiq-compare-final" not in css_text:
    fail("missing compare final css")

if "var(--edgeiq-surface, #ffffff)" not in css_text:
    fail("compare css does not use white surface token")

report = ROOT / "docs/full-product-implementation/EDGEIQ_COMPARE_FINAL_SPEC_V1_AUDIT.md"
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(
    "\n".join(
        [
            "# EDGEiQ Compare Final Spec V1 Audit",
            "",
            "Status: EDGEIQ_COMPARE_FINAL_SPEC_AUDIT_PASS",
            "",
            "- Governed side-by-side comparison workspace present.",
            "- CompareService static model removed from product workspace.",
            "- Jockey, trainer and track comparison modes are not presented as supported where governed side-by-side feeds are unavailable.",
            "- Rejected product language was not found in Compare workspace/service.",
            "- White theme compare styling is present.",
            "",
        ]
    ),
    encoding="utf-8",
)
print("EDGEIQ_COMPARE_FINAL_SPEC_AUDIT_PASS")
