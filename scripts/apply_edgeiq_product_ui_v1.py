from pathlib import Path
import csv
import re
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATA = ROOT / "public" / "data"
CHECKPOINT_MANIFEST = DATA / "edgeiq_product_ui_v1_checkpoint_manifest.csv"
APPLY_MANIFEST = DATA / "edgeiq_product_ui_v1_apply_manifest.csv"
APPLY_SUMMARY = DATA / "edgeiq_product_ui_v1_apply_summary.csv"
APPLY_REPORT = DATA / "edgeiq_product_ui_v1_apply_report.txt"

CHECKPOINT_SUFFIX = "_CHECKPOINT_PRE_PRODUCT_UI_V1_20260630"

MODIFIED_FILES = [
    SRC / "main.tsx",
    SRC / "components" / "RaceIntelligenceScreen.tsx",
]
NEW_FILES = [
    SRC / "styles" / "edgeiqDesignSystem.css",
    SRC / "components" / "ui" / "EdgeiqUi.tsx",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def write_csv(path: Path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def checkpoint_path(path: Path) -> Path:
    suffix = path.suffix
    stem = path.stem
    if path.parent == SRC:
        return path.parent / f"{stem}{CHECKPOINT_SUFFIX}{suffix}"
    return path.parent / f"{stem}{CHECKPOINT_SUFFIX}{suffix}"


def create_checkpoints():
    rows = []
    for path in MODIFIED_FILES:
        cp = checkpoint_path(path)
        if not path.exists():
            rows.append({
                "source_file": rel(path),
                "checkpoint_file": rel(cp),
                "checkpoint_created": "NO",
                "status": "SOURCE_MISSING",
                "created_at": now_iso(),
            })
            continue
        if not cp.exists():
            shutil.copy2(path, cp)
            created = "YES"
            status = "CHECKPOINT_CREATED"
        else:
            created = "NO"
            status = "CHECKPOINT_ALREADY_EXISTS"
        rows.append({
            "source_file": rel(path),
            "checkpoint_file": rel(cp),
            "checkpoint_created": created,
            "status": status,
            "created_at": now_iso(),
        })
    write_csv(CHECKPOINT_MANIFEST, rows)
    return rows


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> tuple[str, bool]:
    start = text.find(start_marker)
    if start < 0:
        return text, False
    end = text.find(end_marker, start)
    if end < 0:
        return text, False
    end += len(end_marker)
    return text[:start] + replacement + text[end:], True


def build_design_css():
    return r'''
:root {
  --edgeiq-bg: #030712;
  --edgeiq-bg-2: #07101b;
  --edgeiq-surface: #0b1220;
  --edgeiq-surface-2: #101827;
  --edgeiq-card: #111c2c;
  --edgeiq-card-2: #162234;
  --edgeiq-border: rgba(116, 134, 160, 0.24);
  --edgeiq-border-strong: rgba(125, 211, 252, 0.28);
  --edgeiq-text: #f8fafc;
  --edgeiq-text-2: #dbe7f3;
  --edgeiq-muted: #94a3b8;
  --edgeiq-muted-2: #64748b;
  --edgeiq-accent: #38bdf8;
  --edgeiq-teal: #2dd4bf;
  --edgeiq-gold: #f5c451;
  --edgeiq-green: #34d399;
  --edgeiq-red: #f87171;
  --edgeiq-shadow: 0 18px 50px rgba(0, 0, 0, 0.36);
  --edgeiq-radius: 8px;
  color-scheme: dark;
}

html, body, #root {
  background: var(--edgeiq-bg) !important;
  color: var(--edgeiq-text-2) !important;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}

.edgeiq-racing-app {
  background:
    radial-gradient(circle at 20% 0%, rgba(56, 189, 248, 0.08), transparent 28%),
    radial-gradient(circle at 80% 10%, rgba(45, 212, 191, 0.06), transparent 26%),
    linear-gradient(180deg, #050914 0%, #030712 45%, #020617 100%) !important;
  min-height: 100vh;
}

.edgeiq-racing-app * {
  box-sizing: border-box;
  letter-spacing: 0;
}

.edgeiq-racing-app header,
.edgeiq-racing-app section,
.edgeiq-racing-app article,
.edgeiq-racing-app details,
.edgeiq-product-surface > div,
.edgeiq-command-workspace,
.edgeiq-workspace-tabs {
  border-radius: var(--edgeiq-radius) !important;
}

.edgeiq-racing-app header,
.edgeiq-racing-app section,
.edgeiq-racing-app article,
.edgeiq-racing-app details {
  border-color: var(--edgeiq-border) !important;
  box-shadow: var(--edgeiq-shadow);
}

.edgeiq-racing-app button {
  border-radius: var(--edgeiq-radius) !important;
  transition: border-color 160ms ease, background 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.edgeiq-racing-app button:hover {
  transform: translateY(-1px);
  border-color: rgba(56, 189, 248, 0.48) !important;
  box-shadow: 0 12px 30px rgba(2, 6, 23, 0.34);
}

.edgeiq-product-home,
.edgeiq-product-meeting,
.edgeiq-product-race {
  max-width: 1760px;
  margin: 0 auto;
}

.edgeiq-product-hero {
  border: 1px solid rgba(125, 211, 252, 0.22) !important;
  background:
    linear-gradient(135deg, rgba(8, 15, 28, 0.98), rgba(3, 8, 16, 0.96)) !important;
  position: relative;
  overflow: hidden;
}

.edgeiq-product-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(56, 189, 248, 0.08), transparent 28%),
    linear-gradient(180deg, rgba(45, 212, 191, 0.05), transparent 36%);
}

.edgeiq-product-hero > * {
  position: relative;
  z-index: 1;
}

.edgeiq-product-home strong,
.edgeiq-product-race strong,
.edgeiq-product-meeting strong {
  color: var(--edgeiq-text);
}

.edgeiq-command-header {
  position: sticky !important;
  top: 10px;
  z-index: 20;
  border: 1px solid rgba(125, 211, 252, 0.24) !important;
  background:
    linear-gradient(135deg, rgba(12, 20, 33, 0.97), rgba(4, 9, 18, 0.95)) !important;
  backdrop-filter: blur(16px);
}

.edgeiq-command-header h2 {
  font-size: clamp(24px, 2.2vw, 36px) !important;
  letter-spacing: 0 !important;
}

.edgeiq-workspace-tabs {
  background: rgba(8, 15, 28, 0.78) !important;
  border: 1px solid rgba(116, 134, 160, 0.22) !important;
}

.edgeiq-command-workspace {
  border: 1px solid rgba(116, 134, 160, 0.22) !important;
  background: linear-gradient(180deg, rgba(10, 18, 31, 0.96), rgba(5, 12, 22, 0.92)) !important;
}

.edgeiq-intel-race-meta span,
.edgeiq-pill,
.condition-pill {
  border-radius: 999px !important;
  border: 1px solid rgba(116, 134, 160, 0.26) !important;
  background: rgba(15, 23, 42, 0.78) !important;
  color: var(--edgeiq-text-2) !important;
}

.edgeiq-source-blocker,
.edgeiq-empty-state,
.edgeiq-warning-state {
  border: 1px solid rgba(245, 196, 81, 0.26);
  background: rgba(245, 196, 81, 0.08);
  color: #fde68a;
  border-radius: var(--edgeiq-radius);
  padding: 12px 14px;
  font-size: 12px;
  line-height: 1.5;
}

.edgeiq-table,
.edgeiq-racing-app table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 6px;
  font-size: 12px;
}

.edgeiq-racing-app th,
.edgeiq-racing-app td {
  border-color: rgba(116, 134, 160, 0.18) !important;
}

.edgeiq-racing-app h1,
.edgeiq-racing-app h2,
.edgeiq-racing-app h3 {
  letter-spacing: 0 !important;
}

.edgeiq-racing-app em {
  color: var(--edgeiq-muted) !important;
}

.edgeiq-racing-app [style*="text-transform: uppercase"] {
  letter-spacing: 0.08em;
}

.edgeiq-racing-app [style*="borderRadius: 10"],
.edgeiq-racing-app [style*="borderRadius: 12"],
.edgeiq-racing-app [style*="borderRadius: 14"],
.edgeiq-racing-app [style*="borderRadius: 16"] {
  border-radius: var(--edgeiq-radius) !important;
}

@media (max-width: 980px) {
  .edgeiq-command-header {
    position: relative !important;
    top: auto;
  }

  .edgeiq-product-hero [style*="gridTemplateColumns"] {
    grid-template-columns: 1fr !important;
  }
}
'''.lstrip()


def build_ui_tsx():
    return r'''
import React from "react";

type Tone = "neutral" | "accent" | "positive" | "warning" | "risk";

const toneClass: Record<Tone, string> = {
  neutral: "edgeiq-ui-neutral",
  accent: "edgeiq-ui-accent",
  positive: "edgeiq-ui-positive",
  warning: "edgeiq-ui-warning",
  risk: "edgeiq-ui-risk",
};

export function EdgeiqBadge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={`edgeiq-ui-badge ${toneClass[tone]}`}>{children}</span>;
}

export function EdgeiqEmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="edgeiq-empty-state">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

export function EdgeiqSourceBlocker({ children }: { children: React.ReactNode }) {
  return <div className="edgeiq-source-blocker">{children}</div>;
}
'''.lstrip()


def apply_main_import(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    import_line = 'import "./styles/edgeiqDesignSystem.css";'
    if import_line in text:
        return False
    anchor = 'import "./terminal/layout/racing-terminal-overrides.css";'
    if anchor in text:
        text = text.replace(anchor, anchor + "\n" + import_line, 1)
    else:
        text += "\n" + import_line + "\n"
    path.write_text(text, encoding="utf-8")
    return True


def apply_race_intelligence(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    changes = []

    product_block = '''    const productCapabilityCards = [
      { title: "Ratings", text: "Prior ratings, recovered form figures and confidence context." },
      { title: "Race Shape", text: "Speed maps, pressure, settling positions and pace advantage." },
      { title: "Market Alignment", text: "Fair price context, live source state and market confirmation." },
      { title: "Connections", text: "Trainer, jockey, partnership and preparation patterns when evidence is material." },
      { title: "Gear / Debutant Intelligence", text: "Source-aware gear and first-starter context without forcing unavailable data." },
    ];'''
    text, ok = replace_between(text, "    const productCapabilityCards = [", "    ];", product_block)
    if ok:
        changes.append("home_capability_cards")

    terminal_block = '''    const terminalPreviewRows = [
      { label: "Data Ready", value: productShellMeetings.length ? `${productShellMeetings.length} meetings loaded` : "Fields loading", tone: productShellMeetings.length ? "#34d399" : "#f5c451" },
      { label: "Intelligence Mode", value: bettingConfidence !== "—" ? bettingConfidence : "Evidence forming", tone: "#7dd3fc" },
      { label: "Market Status", value: livePriceRowCount > 0 ? marketStatus : "Market source unavailable", tone: livePriceRowCount > 0 ? marketStatusTone : "#f5c451" },
      { label: "Gear Status", value: "Current gear source not refreshed", tone: "#f5c451" },
    ];'''
    text, ok = replace_between(text, "    const terminalPreviewRows = [", "    ];", terminal_block)
    if ok:
        changes.append("home_operational_status_cards")

    replacements = [
        ('<div style={{ ...pageStyle, paddingTop: 20 }}>', '<div className="edgeiq-product-home edgeiq-product-surface" style={{ ...pageStyle, paddingTop: 20 }}>'),
        ('<section style={{ ...panelStyle, display: "grid", gap: 28, alignContent: "start", padding: 22, background: "radial-gradient(circle at 82% 8%, rgba(52,211,153,.10), transparent 24%), radial-gradient(circle at 10% 16%, rgba(125,211,252,.10), transparent 28%), linear-gradient(135deg, rgba(8,15,28,.98), rgba(3,8,16,.95))" }}>', '<section className="edgeiq-product-hero" style={{ ...panelStyle, display: "grid", gap: 28, alignContent: "start", padding: 22, background: "radial-gradient(circle at 82% 8%, rgba(52,211,153,.10), transparent 24%), radial-gradient(circle at 10% 16%, rgba(125,211,252,.10), transparent 28%), linear-gradient(135deg, rgba(8,15,28,.98), rgba(3,8,16,.95))" }}>'),
        ('<span style={{ color: "#dbeafe", fontSize: 22, fontWeight: 950 }}>Racing Intelligence Platform</span>', '<span style={{ color: "#dbeafe", fontSize: 22, fontWeight: 950 }}>Adaptive racing intelligence. Not tips. Not noise.</span>'),
        ('Race-shape, form, market, runner and factor intelligence in one terminal.', 'A professional racing intelligence terminal for race shape, ratings, market alignment, connections and runner evidence.'),
        ('>Terminal Preview</span>', '>Operational Status</span>'),
        ('<div style={titleStyle}><span>What EDGEiQ Does</span></div>', '<div style={titleStyle}><span>How EDGEiQ Reads A Race</span><em>Evidence layers, kept source-aware.</em></div>'),
        ('<div style={titleStyle}><span>Today Meetings</span></div>', '<div style={titleStyle}><span>Today\'s Meetings</span><em>Open a card to enter the race terminal.</em></div>'),
        ('<div style={pageStyle}>\n        <section style={panelStyle}>\n          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", flexWrap: "wrap" }}>\n            <div style={{ display: "grid", gap: 6 }}>\n              <button type="button" style={{ ...shellButtonStyle, width: "fit-content", background: "rgba(15,23,42,.9)" }} onClick={() => updateProductView("HOME")}>Back to Home</button>', '<div className="edgeiq-product-meeting edgeiq-product-surface" style={pageStyle}>\n        <section style={panelStyle}>\n          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", flexWrap: "wrap" }}>\n            <div style={{ display: "grid", gap: 6 }}>\n              <button type="button" style={{ ...shellButtonStyle, width: "fit-content", background: "rgba(15,23,42,.9)" }} onClick={() => updateProductView("HOME")}>Back to Home</button>'),
        ('<div style={pageStyle}>\n      <nav style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 10, color: "#94a3b8", fontSize: 11, fontWeight: 900, letterSpacing: ".06em", textTransform: "uppercase" }}>', '<div className="edgeiq-product-race edgeiq-product-surface" style={pageStyle}>\n      <nav style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 10, color: "#94a3b8", fontSize: 11, fontWeight: 900, letterSpacing: ".06em", textTransform: "uppercase" }}>'),
        ('<header style={headerStyle}>', '<header className="edgeiq-command-header" style={headerStyle}>'),
        ('RACE COMMAND BAR', 'PRE-RACE COMMAND'),
        ('<section style={{ ...panelStyle, padding: 10 }}>', '<section className="edgeiq-workspace-tabs" style={{ ...panelStyle, padding: 10 }}>'),
        ('<section style={evidenceSectionStyle}>\n        <div style={titleStyle}>\n          <span>Race Control Room</span>', '<section className="edgeiq-command-workspace" style={evidenceSectionStyle}>\n        <div style={titleStyle}>\n          <span>Intelligence Brief</span>'),
        ('if (!live || live <= 0) return "NO MARKET";', 'if (!live || live <= 0) return "MARKET SOURCE UNAVAILABLE";'),
        ('fallback: "No market signal loaded."', 'fallback: "Market source unavailable."'),
        ('NO MARKET SIGNAL', 'MARKET SOURCE UNAVAILABLE'),
    ]
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new, 1 if old.startswith('<div style={pageStyle}') or old.startswith('<section style=') else -1)
            changes.append(f"replace:{old[:40]}")

    # Keep tab language more product-like without altering mode/state names.
    text = text.replace('{ mode: "ADVANCED", label: "RESEARCH", hint: "Power-user and audit detail" },', '{ mode: "ADVANCED", label: "MARKET", hint: "Market/source state, audit context and power-user detail" },')
    if 'label: "MARKET", hint: "Market/source state' in text:
        changes.append("advanced_tab_market_label")

    path.write_text(text, encoding="utf-8")
    return changes


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    checkpoints = create_checkpoints()
    apply_rows = []

    css_path = SRC / "styles" / "edgeiqDesignSystem.css"
    css_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.write_text(build_design_css(), encoding="utf-8")
    apply_rows.append({"file_path": rel(css_path), "action": "created_or_updated", "category": "DESIGN_SYSTEM_CSS", "status": "OK"})

    ui_path = SRC / "components" / "ui" / "EdgeiqUi.tsx"
    ui_path.parent.mkdir(parents=True, exist_ok=True)
    ui_path.write_text(build_ui_tsx(), encoding="utf-8")
    apply_rows.append({"file_path": rel(ui_path), "action": "created_or_updated", "category": "DESIGN_SYSTEM_COMPONENTS", "status": "OK"})

    main_changed = apply_main_import(SRC / "main.tsx")
    apply_rows.append({"file_path": "src/main.tsx", "action": "updated" if main_changed else "already_current", "category": "APP_ENTRY_IMPORT", "status": "OK"})

    race_changes = apply_race_intelligence(SRC / "components" / "RaceIntelligenceScreen.tsx")
    apply_rows.append({"file_path": "src/components/RaceIntelligenceScreen.tsx", "action": "updated", "category": "PRODUCT_SHELL_HIERARCHY", "status": "OK", "details": "|".join(race_changes)})

    summary = [
        {"metric": "status", "value": "PRODUCT_UI_V1_APPLIED"},
        {"metric": "checkpoint_files", "value": len(checkpoints)},
        {"metric": "design_system_css", "value": rel(css_path)},
        {"metric": "design_system_components", "value": rel(ui_path)},
        {"metric": "frontend_files_modified", "value": 2},
        {"metric": "frontend_files_created", "value": 2},
        {"metric": "backend_model_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "data_schemas_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "YES"},
        {"metric": "built_at", "value": now_iso()},
    ]
    write_csv(APPLY_MANIFEST, apply_rows)
    write_csv(APPLY_SUMMARY, summary, ["metric", "value"])
    APPLY_REPORT.write_text("\n".join([
        "EDGEiQ Product UI V1 Apply Report",
        "==================================",
        "Status: PRODUCT_UI_V1_APPLIED",
        "Checkpoints created before frontend edits.",
        "Design system CSS created at src/styles/edgeiqDesignSystem.css.",
        "Reusable UI primitives created at src/components/ui/EdgeiqUi.tsx.",
        "Home page upgraded with premium product statement, meeting cards and operational status cards.",
        "Race page upgraded with premium command header, sticky hierarchy and source-aware market language.",
        "Backend model changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "Data schemas changed: NO",
        "UI changed: YES",
    ]) + "\n", encoding="utf-8")
    print("PRODUCT_UI_V1_APPLIED")


if __name__ == "__main__":
    main()
