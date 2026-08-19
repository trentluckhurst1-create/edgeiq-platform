export function softmaxPrices(
  runners: { rating: number }[],
  temperature = 6
) {
  if (!runners.length) return [];

  const scaled = runners.map((r) => r.rating / temperature);
  const max = Math.max(...scaled);

  const exps = scaled.map((v) => Math.exp(v - max));
  const sum = exps.reduce((a, b) => a + b, 0);

  return exps.map((e) => {
    const probability = e / sum;
    const price = probability > 0 ? 1 / probability : 999;
    return { probability, price };
  });
}

export function overlayPct(ratedPrice: number, marketPrice: number): number {
  if (!ratedPrice || !marketPrice) return 0;
  return ((marketPrice / ratedPrice) - 1) * 100;
}


