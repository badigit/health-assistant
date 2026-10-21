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
  return points.reduce((latest, point) =>
    Date.parse(point.latest_date || point.date || '') > Date.parse(latest.latest_date || latest.date || '')
      ? point : latest);
}
