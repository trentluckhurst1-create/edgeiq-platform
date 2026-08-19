from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_cell_helper(tsx: str) -> str:
    start = tsx.index("function cell(")
    end = tsx.index("function Silk", start)
    new_block = '''function cell(value: unknown, fallback = "-"): string {
  return text(value, fallback);
}

function epiStatusLabel(value: unknown): string {
  const status = text(value, "");
  return /^available$/i.test(status) ? "" : status;
}

'''
    return tsx[:start] + new_block + tsx[end:]


def replace_epi_row_line(tsx: str) -> str:
    lines = tsx.splitlines()
    matches = [i for i, line in enumerate(lines) if "return row ? <div key={`${row.no}-${row.runner}`}" in line]
    if len(matches) != 1:
        raise RuntimeError(f"EPI row return: expected 1 occurrence, found {len(matches)}")
    lines[matches[0]] = '          const statusLabel = epiStatusLabel(row.status);\n          return row ? <div key={`${row.no}-${row.runner}`} className={`eiq-race-v1__epi-row ${statusLabel ? "has-status" : "is-normal"}`}><b>{index + 1}</b><span>{row.no}</span><strong>{row.runner}</strong><em>{row.value}</em><small>{statusLabel}</small></div> : <div key={`empty-epi-${index}`} className="eiq-race-v1__epi-row is-empty"><b>{index + 1}</b><span>-</span><strong>Insufficient Evidence</strong><em>-</em><small>Awaiting EPI</small></div>;'
    return "\n".join(lines) + "\n"


def remove_conditions_line(tsx: str) -> str:
    lines = tsx.splitlines()
    removed = 0
    kept = []
    for line in lines:
        if '<section className="eiq-race-v1__conditions"' in line:
            removed += 1
            continue
        kept.append(line)
    if removed != 1:
        raise RuntimeError(f"Race conditions line: expected 1 occurrence, found {removed}")
    return "\n".join(kept) + "\n"


def main() -> None:
    tsx = TSX.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    tsx = replace_cell_helper(tsx)
    tsx = replace_once(
        tsx,
        '  const activeRunnerCount = model.runnerBoard.filter((runner) => !runner.scratched).length;\n  const metadata = [["MEETING", meeting || "Meeting Not Published"], ["DATE", date], ["TIME", time], ["DISTANCE", distance || "Distance Not Published"], ["TRACK", track], ["RAIL", rail], ["WEATHER", weather], ["PRIZEMONEY", prize]];\n',
        '  const visibleWhatMatters = model.whatMatters.slice(0, 5);\n  const hasSpeedMapEvidence = model.speedMap.some((zone) => zone.runners.length);\n  const metadata = [["MEETING", meeting || "Meeting Not Published"], ["DATE", date], ["TIME", time], ["DISTANCE", distance || "Distance Not Published"], ["TRACK", track], ["RAIL", rail], ["WEATHER", weather], ["PRIZEMONEY", prize]];\n',
        "visible matters and speed evidence variables",
    )
    tsx = replace_once(
        tsx,
        '<section className="eiq-race-v1__matters" aria-label="What matters today"><header><h2>WHAT MATTERS TODAY</h2><span>{activeRunnerCount ? `${activeRunnerCount} active` : `${model.runnerBoard.length} runners`}</span></header><div>{model.whatMatters.length ? model.whatMatters.slice(0, 5).map((item, index) => <p key={`${item}-${index}`}><span aria-hidden="true" />{item}</p>) : <p><span aria-hidden="true" />Insufficient governed race statements for this race.</p>}</div></section>',
        '<section className="eiq-race-v1__matters" aria-label="What matters today"><header><h2>WHAT MATTERS TODAY</h2><span>{`${visibleWhatMatters.length} active`}</span></header><div>{visibleWhatMatters.length ? visibleWhatMatters.map((item, index) => <p key={`${item}-${index}`}><span aria-hidden="true" />{item}</p>) : <p><span aria-hidden="true" />Insufficient governed race statements for this race.</p>}</div></section>',
        "what matters visible count",
    )
    tsx = replace_once(
        tsx,
        '<article className="eiq-race-v1__speed" aria-label="Speed map preview"><header><h2>SPEED MAP PREVIEW</h2><span>Travel right to left</span></header>{model.speedMap.some((zone) => zone.runners.length) ? <div className="eiq-race-v1__speed-grid">{model.speedMap.map((zone) => <div key={zone.zone} className="eiq-race-v1__speed-zone"><strong>{zone.zone}</strong><div>{zone.runners.length ? zone.runners.slice(0, 5).map((runner) => <span key={`${zone.zone}-${runner.no}-${runner.runner}`}><b>{runner.no}</b>{runner.runner}{runner.earlySpeed ? <em>{runner.earlySpeed}</em> : null}</span>) : <small>Awaiting Speed Evidence</small>}</div></div>)}</div> : <div className="eiq-race-v1__empty">Awaiting Speed Evidence</div>}</article>',
        '<article className={`eiq-race-v1__speed ${hasSpeedMapEvidence ? "is-populated" : "is-empty-state"}`} aria-label="Speed map preview"><header><h2>SPEED MAP PREVIEW</h2><span>Travel right to left</span></header>{hasSpeedMapEvidence ? <div className="eiq-race-v1__speed-grid">{model.speedMap.map((zone) => <div key={zone.zone} className="eiq-race-v1__speed-zone"><strong>{zone.zone}</strong><div>{zone.runners.length ? zone.runners.slice(0, 5).map((runner) => <span key={`${zone.zone}-${runner.no}-${runner.runner}`}><b>{runner.no}</b>{runner.runner}{runner.earlySpeed ? <em>{runner.earlySpeed}</em> : null}</span>) : <small>Awaiting Speed Evidence</small>}</div></div>)}</div> : <div className="eiq-race-v1__empty">Awaiting Speed Evidence</div>}</article>',
        "speed state class",
    )
    tsx = replace_epi_row_line(tsx)
    tsx = remove_conditions_line(tsx)
    tsx = replace_once(tsx, '<th>EDGEIQ</th>', '<th>EDGEiQ PRICE</th>', "EDGEiQ price label")
    tsx = tsx.replace('runner.scratched ? "?" : cell(runner.epi)', 'runner.scratched ? "-" : cell(runner.epi)')
    tsx = tsx.replace('runner.scratched ? "?" : cell(runner.earlySpeed)', 'runner.scratched ? "-" : cell(runner.earlySpeed)')
    tsx = tsx.replace('runner.scratched ? "?" : cell(runner.edgeiqPrice)', 'runner.scratched ? "-" : cell(runner.edgeiqPrice)')

    marker = '/* EDGEIQ RACE WORKSPACE V1 FINAL POLISH */'
    if marker not in css:
        css += '''\n\n/* EDGEIQ RACE WORKSPACE V1 FINAL POLISH */\n.eiq-approved-shell .eiq-race-workspace--race {\n  padding-top: 8px !important;\n  gap: 10px !important;\n}\n.eiq-approved-shell .eiq-race-workspace--race > .eiq-context-tabs {\n  margin: 0 0 8px !important;\n}\n.eiq-approved-shell .eiq-race-v1 {\n  gap: 10px !important;\n}\n.eiq-approved-shell .eiq-race-v1__midrow {\n  align-items: start !important;\n}\n.eiq-approved-shell .eiq-race-v1__speed.is-empty-state {\n  min-height: 126px !important;\n}\n.eiq-approved-shell .eiq-race-v1__speed.is-empty-state .eiq-race-v1__empty {\n  min-height: 72px !important;\n}\n.eiq-approved-shell .eiq-race-v1__speed.is-populated {\n  min-height: 220px !important;\n}\n.eiq-approved-shell .eiq-race-v1__epi-row {\n  grid-template-columns: 30px 40px minmax(0, 1fr) 88px minmax(0, 94px) !important;\n}\n.eiq-approved-shell .eiq-race-v1__epi-row b {\n  color: #0b4ea2 !important;\n  font-size: 14px !important;\n}\n.eiq-approved-shell .eiq-race-v1__epi-row em {\n  color: #0d1b3d !important;\n  font-size: 16px !important;\n  font-weight: 900 !important;\n  letter-spacing: 0 !important;\n}\n.eiq-approved-shell .eiq-race-v1__epi-row strong {\n  font-size: 14px !important;\n  font-weight: 800 !important;\n}\n.eiq-approved-shell .eiq-race-v1__epi-row.is-normal small:empty {\n  display: none !important;\n}\n.eiq-approved-shell .eiq-race-v1__table {\n  min-width: 1252px !important;\n}\n.eiq-approved-shell .eiq-race-v1__table .col-edgeiq {\n  width: 118px !important;\n}\n.eiq-approved-shell .eiq-race-v1__table thead th {\n  font-size: 12px !important;\n  line-height: 14px !important;\n}\n'''

    TSX.write_text(tsx, encoding="utf-8", newline="\n")
    CSS.write_text(css, encoding="utf-8", newline="\n")
    print("EDGEIQ_RACE_WORKSPACE_V1_FINAL_POLISH_APPLIED")


if __name__ == "__main__":
    main()
