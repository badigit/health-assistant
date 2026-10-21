import { beforeEach, expect, it, vi } from 'vitest';
import api from '../api/axios';
import { getBiomarkerTrends } from './analyticsService';

vi.mock('../api/axios', () => ({ default: { get: vi.fn() } }));
vi.mock('./db', () => ({ db: { biomarkerTrends: { put: vi.fn() } } }));
beforeEach(() => vi.clearAllMocks());

it('shares concurrent identical requests and fetches fresh data after completion', async () => {
  let complete!: (value: any) => void;
  vi.mocked(api.get).mockReturnValueOnce(new Promise(resolve => { complete = resolve; }));
  const first = getBiomarkerTrends('tenant', '', 'all-time', 'patient', '1 month');
  const second = getBiomarkerTrends('tenant', '', 'all-time', 'patient', '1 month');
  expect(first).toBe(second);
  expect(api.get).toHaveBeenCalledTimes(1);
  complete({ data: { biomarkers: {} } });
  await first;
  vi.mocked(api.get).mockResolvedValueOnce({ data: { biomarkers: { steps: [] } } });
  expect(await getBiomarkerTrends('tenant', '', 'all-time', 'patient', '1 month'))
    .toEqual({ biomarkers: { steps: [] } });
  expect(api.get).toHaveBeenCalledTimes(2);
});

it('keeps different patients and filters separate', async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { biomarkers: {} } });
  await Promise.all([
    getBiomarkerTrends('tenant', 'steps', 'all-time', 'one'),
    getBiomarkerTrends('tenant', 'steps', 'all-time', 'two'),
    getBiomarkerTrends('tenant', 'sleep-duration', 'all-time', 'one'),
  ]);
  expect(api.get).toHaveBeenCalledTimes(3);
});
