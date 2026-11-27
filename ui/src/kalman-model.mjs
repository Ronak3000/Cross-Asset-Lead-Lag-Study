// Mirrors strategy.py: sample standard deviation, yesterday's position, and
// a cost per unit of position change (a direct reversal costs two units).
export function replaySpread(spread, windowDays, threshold) {
  const z = [], cumulative = [];
  let position = 0, turnover = 0, gross = 0;
  for (let i = 0; i < spread.length; i++) {
    if (i > 0) gross += position * (spread[i] - spread[i - 1]);
    let score = null;
    if (i + 1 >= windowDays) {
      const sample = spread.slice(i + 1 - windowDays, i + 1);
      const mean = sample.reduce((sum, x) => sum + x, 0) / windowDays;
      const variance = sample.reduce((sum, x) => sum + (x - mean) ** 2, 0) / (windowDays - 1);
      if (variance > 0) score = (spread[i] - mean) / Math.sqrt(variance);
    }
    const last = position;
    if (score !== null) {
      if (score > threshold) position = -1;
      else if (score < -threshold) position = 1;
      else if (Math.abs(score) < 0.5) position = 0;
    }
    turnover += Math.abs(position - last);
    z.push(score);
    cumulative.push(gross - 0.005 * turnover);
  }
  return {z, cumulative, turnover};
}
