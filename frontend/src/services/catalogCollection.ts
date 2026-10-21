import type { CatalogItem } from '../types/catalog';
import { listCatalogItems } from './catalogService';

type ListParams = NonNullable<Parameters<typeof listCatalogItems>[1]>;

export async function loadCatalogCollection(
  type: string,
  params: Omit<ListParams, 'limit' | 'offset'>,
  isCurrent: () => boolean = () => true,
): Promise<CatalogItem[] | undefined> {
  const items: CatalogItem[] = [];
  const seen = new Set<string>();
  let expected: number | undefined;
  while (isCurrent()) {
    const page = await listCatalogItems(type, { ...params, limit: 1000, offset: items.length });
    if (!isCurrent()) return undefined;
    expected ??= page.total;
    if (page.total !== expected || !Number.isSafeInteger(expected) || expected < 0) {
      throw new Error('Catalog changed during pagination');
    }
    for (const item of page.items) {
      if (!item.id || seen.has(item.id)) throw new Error('Catalog pagination repeated an item');
      seen.add(item.id);
      items.push(item);
    }
    if (items.length > expected || (items.length < expected && page.items.length === 0)) {
      throw new Error('Catalog pagination is incomplete');
    }
    if (items.length === expected) return items;
  }
  return undefined;
}

export function matchesCatalogSearch(item: CatalogItem, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return true;
  const fields = [item.name, item.slug, item.code, item.description, item.info,
    ...(Array.isArray(item.aliases) ? item.aliases : [])];
  return fields.some((value) => typeof value === 'string' && value.toLocaleLowerCase().includes(needle));
}
