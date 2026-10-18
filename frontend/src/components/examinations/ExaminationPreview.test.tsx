import { cleanup, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { ExaminationPreview } from './ExaminationPreview';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock('../../i18n', () => ({ default: { changeLanguage: async () => undefined } }));
vi.mock('../ui/ExaminationAIActions', () => ({ ExaminationAIActions: () => null }));
vi.mock('../../services/biomarkerService', () => ({ default: { getAllBiomarkers: async () => [] } }));
vi.mock('../../hooks/useBiomarkers', () => ({
  useBiomarkers: () => ({ groupByCategory: () => Object.fromEntries([
    ['positive', { raw: null, normalized: null, state: 'POS', stateDisplay: 'Positive' }, 'state'],
    ['negative', { raw: null, normalized: null, state: 'NEG', stateDisplay: 'Negative' }, 'state'],
    ['text', { raw: '0–2 in field of view', normalized: null }, 'quantity'],
    ['zero', { raw: 0, normalized: 99 }, 'quantity'],
  ].map(([id, value, valueType]) => [String(id), [{
    id, displayName: String(id), valueType, value, unit: { rawSymbol: 'test-unit' },
    referenceRange: { displayText: '--' }, interpretation: 'Unknown', source: {},
  }]])) }),
}));

afterEach(cleanup);

it('shows coded and text results in the preview and keeps the raw numeric value', () => {
  render(<MemoryRouter><ExaminationPreview selectedExam={{ id: 'exam', examination_date: '2024-01-01' }} examDocuments={[]} onDocumentClick={() => undefined} onInfoClick={() => undefined} /></MemoryRouter>);
  expect(screen.getByText('Positive')).toBeInTheDocument();
  expect(screen.getByText('Negative')).toBeInTheDocument();
  expect(screen.getByText('0–2 in field of view')).toBeInTheDocument();
  expect(within(screen.getByText('Positive').closest('tr')!).queryByText('test-unit')).toBeNull();
  expect(within(screen.getByText('zero').closest('tr')!).getByText(/^0(?:\.0+)?$/)).toBeInTheDocument();
  expect(screen.queryByText('99')).toBeNull();
});
