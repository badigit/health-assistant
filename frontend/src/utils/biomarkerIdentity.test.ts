import { describe, it, expect } from 'vitest';
import { resolveBiomarkerKey, latestBiomarkerPoint, datedBiomarkerPoints } from './biomarkerIdentity';
import { computeStatus } from './biomarkerUtils';

describe('Canonical wearable identity and latest reading', () => {
  it('keeps undated history intact while excluding it from the time axis', () => {
    const rows = [{ date: '', value: 140 }, { date: '2026-01-01', value: 134 }];
    expect(datedBiomarkerPoints(rows)).toEqual([rows[1]]);
    expect(rows).toHaveLength(2);
  });
  it('resolves old English dashboard cards and source-slug cards to one canonical series', () => {
    const series = { 'systolic-bp': [{ name: 'Давление', aliases: ['Systolic blood pressure'], source_slugs: ['apple-health-systolic-bp'] }] };
    expect(resolveBiomarkerKey('Systolic blood pressure', series)).toBe('systolic-bp');
    expect(resolveBiomarkerKey('apple-health-systolic-bp', series)).toBe('systolic-bp');
  });
  it('uses actual measurement time rather than bucket time', () => {
    const clinical = { date: '2026-10-02T10:00:00Z', value: 120 };
    const wearable = { date: '2026-10-01T00:00:00Z', latest_date: '2026-10-20T10:00:00Z', value: 125 };
    expect(latestBiomarkerPoint([wearable, clinical])).toBe(wearable);
  });
  it('does not let undated legacy results hide a dated measurement', () => {
    const legacy = { date: '', value: null };
    const latest = { date: '2026-10-01T00:00:00Z', latest_date: '2026-10-02T13:00:00Z', value: 134 };
    expect(latestBiomarkerPoint([legacy, latest])).toBe(latest);
    expect(latestBiomarkerPoint([latest, legacy])).toBe(latest);
  });
  it('does not call missing data normal even with a stale interpretation', () => {
    expect(computeStatus(undefined, 60, 100, 'Normal')).toBe('Unknown');
    expect(computeStatus('--', undefined, undefined, 'Normal')).toBe('Unknown');
    expect(computeStatus(70, undefined, undefined, null)).toBe('Unknown');
    expect(computeStatus(70, 60, 100, null)).toBe('Normal');
    expect(computeStatus(120, 60, 100, null)).toBe('High');
  });
});
