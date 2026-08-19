export function getLineColour(index: number): string {
  const hue = (index * 37) % 360;
  return `hsl(${hue}, 85%, 60%)`;
}

