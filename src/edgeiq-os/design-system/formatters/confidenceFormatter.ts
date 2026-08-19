export function formatConfidenceLabel(confidence: number): string {
  if (confidence >= 85) return "Very High";
  if (confidence >= 70) return "High";
  if (confidence >= 55) return "Moderate";
  if (confidence >= 40) return "Developing";
  return "Low";
}
