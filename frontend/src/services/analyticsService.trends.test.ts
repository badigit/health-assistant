import { beforeEach, expect, it, vi } from 'vitest';
import api from '../api/axios';
import { getBiomarkerTrends, getCachedBiomarkerTrends } from './analyticsService';

const cache = vi.hoisted(() => {
  const collection = { reverse: vi.fn(), first: vi.fn() };
  collection.reverse.mockReturnValue(collection);
  return { collection, put: vi.fn(), where: vi.fn(() => collection) };
});

vi.mock('../api/axios', () => ({ default: { get: vi.fn() } }));
vi.mock('./db', () => ({ db: { biomarkerTrends: { put: cache.put, where: cache.where } } }));
beforeEach(() => vi.clearAllMocks());

it('reads the newest legacy cache row and updates that row instead of appending snapshots', async () => {
  cache.collection.first.mockResolvedValue({ id: 42, data: { biomarkers: { old: [] } } });
  expect(await getCachedBiomarkerTrends('patient', 'all-time')).toEqual({ biomarkers: { old: [] } });
  expect(cache.collection.reverse).toHaveBeenCalled();
  vi.mocked(api.get).mockResolvedValueOnce({ data: { biomarkers: { steps: [] } } });
  await getBiomarkerTrends('tenant', '', 'all-time', 'patient');
  expect(cache.put).toHaveBeenCalledWith(expect.objectContaining({ id: 42, data: { biomarkers: { steps: [] } } }));
});

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

it('still returns successful network data when local caching fails', async () => {
  const warning = vi.spyOn(console, 'warn').mockImplementation(() => {});
  cache.collection.first.mockRejectedValueOnce(new Error('storage unavailable'));
  vi.mocked(api.get).mockResolvedValueOnce({ data: { biomarkers: { steps: [] } } });
  expect(await getBiomarkerTrends('tenant', '', 'all-time', 'patient')).toEqual({ biomarkers: { steps: [] } });
  expect(warning).toHaveBeenCalled();
  warning.mockRestore();
});
