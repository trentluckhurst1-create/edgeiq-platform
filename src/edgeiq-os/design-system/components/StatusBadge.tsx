import { formatIntelligenceStatus } from "../formatters/statusFormatter";

type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`eiq-ds-status eiq-ds-status--${status.toLowerCase()}`}>{formatIntelligenceStatus(status)}</span>;
}
