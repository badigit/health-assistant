import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BiomarkerSnapshotCard } from '../BiomarkerSnapshotCard';
import { BiomarkerKpiStrip } from '../BiomarkerKpiStrip';
import { meanExactReadings } from '../../../utils/biomarkerUtils';
import type { Biomarker } from '../../../types/biomarker';
import type { BiomarkerPrecisionProfile } from '../../../utils/biomarkerUtils';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
const marker = { id: 'q', slug: 'density', name: 'Density', aliases: [], value_type: 'quantity' } as Biomarker;
const precision = { mode: 'stored', default: 0, below_30: 1, below_10: 1, below_3: 2, below_1: 3 } as BiomarkerPrecisionProfile;

describe('biomarker summaries', () => {
  it.each([BiomarkerSnapshotCard, BiomarkerKpiStrip])('shows a source bound and reference without undefined', Component => {
    const { container } = render(<Component biomarker={marker} trends={[{ value: null, display_value: '<7', comparator: '<', unit: 'mg/L', reference_range_text: '0–8 mg/L', date: new Date().toISOString() }]} precisionProfile={precision} interpretation="Unknown" />);
    expect(screen.getByText('<7')).toBeTruthy();
    expect(screen.getByText('0–8 mg/L')).toBeTruthy();
    expect(container.textContent).not.toContain('undefined');
  });
  it('averages exact samples, preserving zero and excluding censored or categorical values', () => {
    expect(meanExactReadings([{ value: 0 }, { value: 2 }, { value: null, comparator: '<' }, { value: 'Negative' }])).toBe(1);
    expect(meanExactReadings([{ value: 7, comparator: '<' }])).toBeNull();
  });
});
