export function formatPriority(priority: string): string {
  if (priority === "CRITICAL") return "Critical Watch";
  if (priority === "HIGH") return "High Attention";
  if (priority === "NORMAL") return "Routine Monitoring";
  if (priority === "LOW") return "Low Attention";
  return priority;
}
