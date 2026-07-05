type RatingHoverMetric = {
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
