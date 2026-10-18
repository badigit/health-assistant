export function extractReferenceRange(data: any): { min: number | null; max: number | null } {
  const empty = { min: null, max: null };
  if (!data) return empty;
  if (Array.isArray(data)) return data.length === 1 ? extractReferenceRange(data[0]) : empty;
  if (typeof data === 'string') {
    const number = '([+-]?(?:\\d+(?:[.,]\\d+)?|[.,]\\d+))';
    const unit = '(?:\\s*[%a-zA-ZµμмкглдЕМО/0-9^³².*-]+)?';
    const interval = data.trim().match(new RegExp('^' + number + '\\s*[-–—]\\s*' + number + unit + '$', 'u'));
    const numeric = (s: string) => Number(s.replace(',', '.'));
    if (interval) {
      const min = numeric(interval[1]), max = numeric(interval[2]);
      return min <= max ? { min, max } : empty;
    }
    const bound = data.trim().match(new RegExp('^(<=|>=|<|>|≤|≥)\\s*' + number + unit + '$', 'u'));
    if (bound) return ['<', '<=', '≤'].includes(bound[1])
      ? { min: null, max: numeric(bound[2]) } : { min: numeric(bound[2]), max: null };
    return empty;
  }
  const value = (v: any) => {
    const n = v && typeof v === 'object' ? v.value : v;
    if (n == null || n === '') return null;
    const converted = Number(n);
    return Number.isFinite(converted) ? converted : null;
  };
  const min = value(data.min ?? data.low ?? data.minimum ?? data.reference_range_min ?? data.biomarker_reference_range_min);
  const max = value(data.max ?? data.high ?? data.maximum ?? data.reference_range_max ?? data.biomarker_reference_range_max);
  if (min != null || max != null) return min != null && max != null && min > max ? empty : { min, max };
  return typeof data.text === 'string' ? extractReferenceRange(data.text) : empty;
}
