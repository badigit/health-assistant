import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { BiomarkerStatusIndicator } from './BiomarkerStatusIndicator';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (_key: string, fallback: string) => fallback }) }));
afterEach(cleanup);

it.each(['NoData', 'Unknown', 'Abnormal', 'Warning'])('does not show a normal check for %s', interpretation => {
  const { container } = render(<BiomarkerStatusIndicator interpretation={interpretation} />);
  expect(container.querySelector('.lucide-circle-check-big')).toBeNull();
  expect(container.querySelector('[class*="text-green"]')).toBeNull();
});

it('retains the normal check only for an explicit normal status', () => {
  const { container } = render(<BiomarkerStatusIndicator interpretation="Normal" />);
  expect(container.querySelector('[class*="text-green"]')).not.toBeNull();
});
