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
