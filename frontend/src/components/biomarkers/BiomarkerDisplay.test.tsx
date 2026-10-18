import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useSettingsStore } from '../../store/slices/settingsSlice';
import { BiomarkerList } from './BiomarkerList';
import { BiomarkerResultCard } from './BiomarkerResultCard';
import type { BiomarkerObservation } from '../../types/biomarker';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock('../../i18n', () => ({ default: { changeLanguage: async () => undefined } }));
vi.mock('../charts/LineChart', () => ({ default: () => null }));
vi.mock('./UnmappedBiomarkerMenu', () => ({ UnmappedBiomarkerMenu: () => null }));

const marker = {
  id: 'test-observation', definitionId: 'test-definition', displayName: 'Test biomarker',
  value: { raw: 97.5, normalized: 97.5 },
  unit: { rawSymbol: 'mg/L', normalizedSymbol: 'mg/L' },
  referenceRange: { displayText: '0–104', min: 0, max: 104 },
  interpretation: 'Normal', source: { date: '2026-01-01' },
} as BiomarkerObservation;

afterEach(() => {
  cleanup();
  useSettingsStore.setState({ compactDashboard: false, biomarkerDisplayMode: 'fixed' });
});

describe('resolved appearance settings', () => {
  it.each(['table', 'list', 'grid'] as const)('renders coded and free-text values in %s mode', viewMode => {
    const qualitative = { ...marker, id: 'state', displayName: 'Qualitative', valueType: 'state', value: { raw: null, normalized: null, state: 'NEG', stateDisplay: 'Negative' } } as BiomarkerObservation;
    const text = { ...marker, id: 'text', displayName: 'Text result', value: { raw: '0–2 in field of view', normalized: '0–2 in field of view' }, interpretation: 'Unknown' } as BiomarkerObservation;
    render(<MemoryRouter><BiomarkerList groupedData={[["Lab", [qualitative, text]]]} viewMode={viewMode} showCharts={false} /></MemoryRouter>);
    expect(screen.getByText('Negative')).toBeInTheDocument();
    expect(screen.getByText('0–2 in field of view')).toBeInTheDocument();
  });

  it('uses stored precision and tenant density in the biomarker table', () => {
    useSettingsStore.setState({ compactDashboard: true, biomarkerDisplayMode: 'stored', biomarkerPrecision: 0 });
    const { container } = render(<MemoryRouter>
      <BiomarkerList groupedData={[["Lab", [marker]]]} viewMode="table" showCharts={false} />
    </MemoryRouter>);
    expect(screen.getByText('97.5')).toBeInTheDocument();
    expect(container.querySelector('[data-density="compact"]')).not.toBeNull();
  });

  it('allows an explicit comfortable layout to override tenant density', () => {
    useSettingsStore.setState({ compactDashboard: true });
    const { container } = render(<MemoryRouter>
      <BiomarkerList groupedData={[["Lab", [marker]]]} viewMode="table" compact={false} />
    </MemoryRouter>);
    expect(container.querySelector('[data-density="comfortable"]')).not.toBeNull();
  });

  it('uses the same stored precision in observation detail cards', () => {
    useSettingsStore.setState({ biomarkerDisplayMode: 'stored', biomarkerPrecision: 0 });
    render(<BiomarkerResultCard b={marker} />);
    expect(screen.getByText('97.5')).toBeInTheDocument();
    expect(screen.queryByText('98')).toBeNull();
  });
});
