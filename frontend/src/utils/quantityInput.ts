export function parseQuantityInput(input: string): { value: number; comparator?: '<' | '<=' | '>' | '>=' } {
  const match = input.trim().match(/^(<=|>=|<|>|≤|≥)?\s*([+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?:e[+-]?\d+)?)$/i);
  if (!match || !Number.isFinite(Number(match[2].replace(',', '.')))) throw new Error('Invalid quantity');
  const comparator = match[1] === '≤' ? '<=' : match[1] === '≥' ? '>=' : match[1];
  return { value: Number(match[2].replace(',', '.')), ...(comparator ? { comparator: comparator as '<' | '<=' | '>' | '>=' } : {}) };
}
