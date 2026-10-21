export function resolveBiomarkerKey(key: string, series: Record<string, any[]>): string | undefined {
  const normalize = (s: string) => s.trim().toLowerCase().replace(/\s+/g, '-');
  const wanted = normalize(key);
  return Object.keys(series).find(slug => normalize(slug) === wanted)
    ?? Object.keys(series).find(slug => series[slug]?.some(point =>
      [point.name, ...(point.aliases || []), ...(point.source_slugs || [])]
        .some(value => typeof value === 'string' && normalize(value) === wanted)));
}

export function latestBiomarkerPoint<T extends { date?: string; latest_date?: string }>(points?: T[]): T | null {
  if (!points?.length) return null;
  const timestamp = (point: T) => {
    const parsed = Date.parse(point.latest_date || point.date || '');
    return Number.isFinite(parsed) ? parsed : -Infinity;
  };
  return points.reduce((latest, point) =>
    timestamp(point) > timestamp(latest)
      ? point : latest);
}
