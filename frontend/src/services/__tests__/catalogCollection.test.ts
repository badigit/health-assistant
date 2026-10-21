import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { loadCatalogCollection, matchesCatalogSearch } from '../catalogCollection';
import { listCatalogItems } from '../catalogService';
import { getFacetsForType } from '../../components/catalog/catalogFacetRegistry';
import { useFilterState } from '../../components/ui/filters';
import type { CatalogItem } from '../../types/catalog';

vi.mock('../catalogService', () => ({ listCatalogItems: vi.fn() }));
const list = vi.mocked(listCatalogItems);
const items: CatalogItem[] = Array.from({ length: 75 }, (_, index) => ({
  id: String(index), name: `Metric ${index}`, is_telemetry: index >= 60,
  preferred_unit_symbol: index >= 60 ? 'mmHg' : 'count',
  coding_system: index >= 60 ? 'custom' : 'loinc',
  category: index >= 60 ? 'Pressure' : 'Other',
  code: `CODE-${index}`, aliases: [`source-alias-${index}`],
}));

beforeEach(() => { list.mockReset(); });

describe('complete catalog filtering', () => {
  it('loads every server page and combines search with telemetry, category, unit and coding filters', async () => {
    list.mockResolvedValueOnce({ items: items.slice(0, 50), total: 75 });
    list.mockResolvedValueOnce({ items: items.slice(50), total: 75 });
    const collection = await loadCatalogCollection('biomarker', { include: 'relations', scope: 'user' });
    expect(collection).toHaveLength(75);
    expect(list.mock.calls[1]).toEqual(['biomarker', { include:'relations', scope:'user',limit:1000,offset:50 }]);
    const { result } = renderHook(() => useFilterState(getFacetsForType('biomarker')));
    act(() => {
      result.current.set('is_telemetry', { kind:'toggle',on:true });
      for (const [id, value] of [['category','Pressure'],['unit','mmHg'],['coding_system','custom']]) {
        result.current.set(id,{kind:'multi',values:[value]});
      }
    });
    expect(result.current.applyFilters(collection!)).toHaveLength(15);
    expect(result.current.applyFilters(collection!).filter((item) => matchesCatalogSearch(item,'SOURCE-ALIAS-74'))).toEqual([items[74]]);
    expect(collection!.filter((item) => matchesCatalogSearch(item,'CODE-74'))).toEqual([items[74]]);
    act(() => result.current.clearAll());
    expect(result.current.applyFilters(collection!)).toHaveLength(75);
    const unitFacet = getFacetsForType('biomarker').find((facet) => facet.id==='unit')!;
    expect(unitFacet.getOptions!(collection!).map((option) => option.value)).toContain('mmHg');
  });

  it.each([
    [{items:items.slice(0,50),total:75},{items:[items[0]],total:75}],
    [{items:items.slice(0,50),total:75},{items:[],total:75}],
    [{items:items.slice(0,50),total:75},{items:items.slice(50),total:76}],
  ])('rejects duplicate, incomplete or changing snapshots', async (first, second) => {
    list.mockResolvedValueOnce(first).mockResolvedValueOnce(second);
    await expect(loadCatalogCollection('biomarker',{})).rejects.toThrow();
  });

  it('discards an obsolete request without fetching its remaining pages', async () => {
    let current = true;
    list.mockImplementationOnce(async () => { current=false; return {items:items.slice(0,50),total:75}; });
    expect(await loadCatalogCollection('biomarker',{},()=>current)).toBeUndefined();
    expect(list).toHaveBeenCalledTimes(1);
  });

  it('keeps empty catalogs empty and propagates page errors', async () => {
    list.mockResolvedValueOnce({items:[],total:0});
    expect(await loadCatalogCollection('allergy',{})).toEqual([]);
    list.mockRejectedValueOnce(new Error('offline'));
    await expect(loadCatalogCollection('allergy',{})).rejects.toThrow('offline');
  });
});
