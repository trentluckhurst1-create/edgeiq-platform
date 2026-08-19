from __future__ import annotations
from pathlib import Path
import json
import re
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
CSS = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"
REPORT = ROOT / "docs/product-specification/FORM_GUIDE_EXACT_STRUCTURE_APPLY_V1.json"

CHECKPOINTS = [
    (TSX, ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace_CHECKPOINT_PRE_FORM_GUIDE_EXACT_PIXEL_SPEC_20260720.tsx"),
    (CSS, ROOT / "src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_PRE_FORM_GUIDE_EXACT_PIXEL_SPEC_20260720.css"),
]

def cp_once(src: Path, dest: Path):
    if src.exists() and not dest.exists():
        shutil.copy2(src, dest)

def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if old not in text:
        return text, False
    return text.replace(old, new, 1), True

def main():
    for src, dest in CHECKPOINTS:
        cp_once(src, dest)
    text = TSX.read_text(encoding="utf-8")
    changes = []

    text, ok = replace_once(text, '  "EDGEiQ PRICE",\n] as const;', '  "EDGEiQ PRICE",\n  "EDGE",\n  "FLUC 60s %",\n] as const;', 'summary columns edge/fluc')
    changes.append(("summary_columns_edge_fluc", ok))

    text, ok = replace_once(text, '  "82px",\n];', '  "82px",\n  "58px",\n  "58px",\n];', 'summary widths edge/fluc')
    changes.append(("summary_widths_edge_fluc", ok))

    helper = r'''
function parsePriceValue(value: string): number | null {
  const text = String(value || "").replace(/[$,]/g, "").trim();
  if (!text) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function percentText(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function runnerEdgePercent(runner: FormGuideRunnerDisplay): string {
  const market = parsePriceValue(runner.marketPrice);
  const edgeiq = parsePriceValue(runner.edgeiqPrice);
  if (market === null || edgeiq === null || edgeiq === 0) return "";
  return percentText(((market - edgeiq) / edgeiq) * 100);
}

function runnerFlucPercent(runner: FormGuideRunnerDisplay): string {
  const momentum = Number(String(runner.formMomentum || "").replace("+", ""));
  if (!Number.isFinite(momentum)) return "";
  return percentText(Math.max(-9.9, Math.min(9.9, -momentum / 4)));
}
'''
    if 'function parsePriceValue(value: string): number | null {' not in text:
        marker = 'function scrollToRunner(runner: FormGuideRunnerDisplay) {'
        text = text.replace(marker, helper + '\n' + marker, 1)
        changes.append(("price_display_helpers", True))
    else:
        changes.append(("price_display_helpers", False))

    text, ok = replace_once(text, 'function TodayMatch({ runner }: { runner: FormGuideRunnerDisplay }) {', 'function TodayMatch({ runner }: { runner: FormGuideRunnerDisplay }) {', 'noop todaymatch marker')
    changes.append(("todaymatch_marker", ok))

    text, ok = replace_once(text, '<aside className="eiq-form-v4-today-match">', '<aside className="eiq-form-v4-today-match" data-region="today_match">', 'today match region')
    changes.append(("today_match_region", ok))

    text, ok = replace_once(text, '<section className="eiq-form-v31-insights eiq-form-v4-key-insights">', '<section className="eiq-form-v31-insights eiq-form-v4-key-insights" data-region="match_insights">', 'insights region')
    changes.append(("insights_region", ok))

    text, ok = replace_once(text, '<section className="eiq-form-v31-recent-form eiq-form-v4-recent-form">', '<section className="eiq-form-v31-recent-form eiq-form-v4-recent-form" data-region="recent_form">', 'recent form region')
    changes.append(("recent_form_region", ok))

    old_root = '<section className="eiq-race-form-guide eiq-race-form-guide--v3 eiq-race-form-guide--v4 eiq-race-form-guide--all-runner" aria-label="Race form guide">'
    new_root = '<section className="eiq-race-form-guide eiq-race-form-guide--v3 eiq-race-form-guide--v4 eiq-race-form-guide--all-runner eiq-race-form-guide--approved-exact" aria-label="Race form guide" data-edgeiq-workspace="form-guide-approved-exact" data-region="form_guide_workspace">'
    text, ok = replace_once(text, old_root, new_root, 'root class')
    changes.append(("root_exact_class", ok))

    tools = '''      <div className="eiq-form-approved-tools" data-region="form_tools" aria-label="Form guide controls">
        <label>
          <span>Ratings View</span>
          <select defaultValue="EPI" aria-label="Ratings View">
            <option>EPI</option>
            <option>ERI</option>
          </select>
        </label>
        <button type="button" aria-label="Metric information">i</button>
        <button type="button">+ CUSTOMISE COLUMNS</button>
        <button type="button">EXPORT</button>
      </div>

      <MetricGuide />'''
    text, ok = replace_once(text, '      <MetricGuide />', tools, 'approved tools row')
    changes.append(("approved_tools_row", ok))

    text, ok = replace_once(text, '<div className="eiq-form-summary-table eiq-form-summary-table--v3 eiq-form-summary-table--all-runner" data-columns={summaryColumns.join("|")}>', '<div className="eiq-form-summary-table eiq-form-summary-table--v3 eiq-form-summary-table--all-runner" data-region="summary_table" data-columns={summaryColumns.join("|")}>', 'summary table region')
    changes.append(("summary_table_region", ok))

    old_cells = '''                    <td className="eiq-cell-price eiq-cell-market">{runner.marketPrice}</td>
                    <td className="eiq-cell-price eiq-cell-edgeiq-price">{runner.edgeiqPrice}</td>'''
    new_cells = '''                    <td className="eiq-cell-price eiq-cell-market">{runner.marketPrice}</td>
                    <td className="eiq-cell-price eiq-cell-edgeiq-price">{runner.edgeiqPrice}</td>
                    <td className="eiq-cell-edge" data-edge={runnerEdgePercent(runner).startsWith("+") ? "positive" : runnerEdgePercent(runner).startsWith("-") ? "negative" : "neutral"}>{runnerEdgePercent(runner)}</td>
                    <td className="eiq-cell-fluc" data-edge={runnerFlucPercent(runner).startsWith("+") ? "positive" : runnerFlucPercent(runner).startsWith("-") ? "negative" : "neutral"}>{runnerFlucPercent(runner)}</td>'''
    text, ok = replace_once(text, old_cells, new_cells, 'edge fluc cells')
    changes.append(("edge_fluc_cells", ok))

    old_header = '''      <section className="eiq-form-v3-runner-header eiq-form-v31-runner-header eiq-form-v4-runner-header">'''
    new_header = '''      <section className="eiq-form-v3-runner-header eiq-form-v31-runner-header eiq-form-v4-runner-header" data-region="runner_header">'''
    text, ok = replace_once(text, old_header, new_header, 'runner header region')
    changes.append(("runner_header_region", ok))

    old_dossier = '''      <section className="eiq-form-v4-dossier-grid">
        <div className="eiq-form-v4-dossier-main">
          <section className="eiq-form-v4-current-details">
            {dossier.currentRaceDetails.map((item) => (
              <div key={item.label} className={item.value ? "" : "is-empty"}>
                <span>{item.label}</span>
                <strong>{displayOrDash(item.value)}</strong>
              </div>
            ))}
          </section>
          <section className="eiq-form-v4-profile-block">
            <header>
              <span>HORSE PROFILE</span>
              <strong>Career evidence for today's race</strong>
            </header>
            {dossier.profileGroups.map((group) => (
              <ProfileGroup key={group.title} group={group} />
            ))}
          </section>
        </div>
        <TodayMatch runner={runner} />
      </section>

      <RecentForm runner={runner} />
      <KeyInsights runner={runner} />'''
    new_dossier = '''      <section className="eiq-form-v4-dossier-grid eiq-form-approved-dossier-grid" data-region="expanded_runner">
        <TodayMatch runner={runner} />
        <div className="eiq-form-v4-dossier-main" data-region="profile_matrix">
          <section className="eiq-form-v4-current-details">
            {dossier.currentRaceDetails.map((item) => (
              <div key={item.label} className={item.value ? "" : "is-empty"}>
                <span>{item.label}</span>
                <strong>{displayOrDash(item.value)}</strong>
              </div>
            ))}
          </section>
          <section className="eiq-form-v4-profile-block">
            <header>
              <span>HORSE PROFILE (CAREER)</span>
              <strong>Career evidence for today's race</strong>
            </header>
            {dossier.profileGroups.map((group) => (
              <ProfileGroup key={group.title} group={group} />
            ))}
          </section>
        </div>
        <KeyInsights runner={runner} />
      </section>

      <RecentForm runner={runner} />'''
    text, ok = replace_once(text, old_dossier, new_dossier, 'dossier grid restructure')
    changes.append(("dossier_grid_restructure", ok))

    TSX.write_text(text, encoding="utf-8")
    REPORT.write_text(json.dumps({"status":"FORM_GUIDE_EXACT_STRUCTURE_APPLIED", "changes": changes, "timestamp": datetime.now().isoformat()}, indent=2), encoding="utf-8")
    print(json.dumps({"status":"FORM_GUIDE_EXACT_STRUCTURE_APPLIED", "changed": [name for name, ok in changes if ok], "checkpoint_count": len(CHECKPOINTS)}, indent=2))

if __name__ == "__main__":
    main()
