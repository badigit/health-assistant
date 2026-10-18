import { describe, it, expect } from 'vitest';
import { extractReferenceRange } from '../referenceRange';
import { parseQuantityInput } from '../quantityInput';
import { computeStatus } from '../biomarkerUtils';

describe('source reference ranges', () => {
  it.each([
    ['4.1–5.9 mmol/L', { min: 4.1, max: 5.9 }],
    ['-2,5 - 3,5', { min: -2.5, max: 3.5 }],
    ['≤60 min', { min: null, max: 60 }],
    ['<1.03 — low; ≥1.55 — high', { min: null, max: null }],
    ['Adults 3-5; children 1-2', { min: null, max: null }],
    ['Risk-dependent targets: <3.4; <2.6; <1.8', { min: null, max: null }],
  ])('only parses a single complete interval: %s', (source, expected) => {
    expect(extractReferenceRange(source)).toEqual(expected);
  });
  it('does not choose an arbitrary population from multiple reference ranges', () => {
    expect(extractReferenceRange([{ low: { value: 1 }, high: { value: 2 } }, { high: { value: 3 } }])).toEqual({ min: null, max: null });
  });
  it('retains zero and explicit structured bounds', () => {
    expect(extractReferenceRange([{ low: { value: 0 }, high: { value: 6 }, text: 'source wording' }])).toEqual({ min: 0, max: 6 });
  });
});

describe('quantity bounds', () => {
  it.each(['<', '<=', '>', '>='])('preserves %s through editing and status', comparator => {
    expect(parseQuantityInput(`${comparator}7.25`)).toEqual({ comparator, value: 7.25 });
    expect(computeStatus(`${comparator}7.25`, 0, 10, null)).toBe('Unknown');
  });
  it('accepts an exact zero and rejects partial parses', () => {
    expect(parseQuantityInput('0')).toEqual({ value: 0 });
    expect(() => parseQuantityInput('7 not measured')).toThrow();
    expect(() => parseQuantityInput('NaN')).toThrow();
  });
});
