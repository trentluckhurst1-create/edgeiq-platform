from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

start_marker = ' {ratingHover ? ('
end_marker = ' <footer className="edgeiq-home-v4-footer edgeiq-product-v4-footer">'

start = text.find(start_marker)
if start == -1:
    raise SystemExit("ratingHover start marker not found")

end = text.find(end_marker, start)
if end == -1:
    raise SystemExit("footer marker after ratingHover not found")

component = '''type RatingHoverMetric = {
  label: string;
  value: string;
  tone?: string;
};

type RatingHoverCard = {
  title: string;
  subtitle?: string;
  footer?: string;
  x: number;
  y: number;
  metrics: RatingHoverMetric[];
};

type RatingHoverTooltipProps = {
  ratingHover: RatingHoverCard | null;
};

export function RatingHoverTooltip({ ratingHover }: RatingHoverTooltipProps) {
  if (!ratingHover) return null;

  return (
    <div className="edgeiq-performance-tooltip" style={{ left: ratingHover.x, top: ratingHover.y }} role="tooltip">
      <strong>{ratingHover.title}</strong>
      {ratingHover.subtitle ? <em>{ratingHover.subtitle}</em> : null}
      <div>
        {ratingHover.metrics.map((metric) => <span key={`rating-hover-${metric.label}`}><b>{metric.label}</b><i style={{ color: metric.tone || undefined }}>{metric.value}</i></span>)}
      </div>
      {ratingHover.footer ? <p>{ratingHover.footer}</p> : null}
    </div>
  );
}
'''

Path("src/components/overlays").mkdir(parents=True, exist_ok=True)
Path("src/components/overlays/RatingHoverTooltip.tsx").write_text(component, encoding="utf-8")

replacement = ' <RatingHoverTooltip ratingHover={ratingHover} />\n'
text = text[:start] + replacement + text[end:]

import_line = 'import { RatingHoverTooltip } from "./overlays/RatingHoverTooltip";\n'
if import_line.strip() not in text:
    marker = 'import { RaceLabWorkspace } from "./workspaces/RaceLabWorkspace";\n'
    if marker in text:
        text = text.replace(marker, marker + import_line, 1)
    else:
        first_import_end = text.find("\n", text.find("import "))
        text = text[:first_import_end + 1] + import_line + text[first_import_end + 1:]

path.write_text(text, encoding="utf-8")
print("[TOOLTIP_EXTRACT] RatingHoverTooltip extracted")
