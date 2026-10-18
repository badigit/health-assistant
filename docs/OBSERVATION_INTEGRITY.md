# Observation integrity

An imported result retains its source document, source date, original wording,
and reviewed catalog association. A successful write alone does not establish
that the association or numeric scale is correct.

## Values and references

- Exact values use `value_quantity` with a finite numeric `value` and an explicit
  unit. Convert units before writing only when the conversion is justified.
- Bounds use the FHIR `value_quantity.comparator`: `<`, `<=`, `>`, or `>=`.
  A bound is displayed literally and never becomes an exact numeric trend point.
- Categorical results use `value_codeable_concept` and a permitted catalog state.
  “Not detected” must not silently become a numeric zero.
- Source intervals such as “0–2 per field” may remain `value_string` attached
  to the appropriate quantity definition. Never replace an interval with its
  endpoint or average.
- Clinical conclusions, tests not performed, execution status, and calculations
  not produced are explicit non-measurement exceptions. Review all other
  unmapped rows before accepting an import.
- Structured reference bounds take precedence. A free-text reference is parsed
  only when the entire string is one interval or one bound. Multiple populations
  and risk-dependent targets remain source text.

## Updates and verification

`PUT /observations/{id}` supports value replacement, `reference_range`,
`interpretation`, and a tenant-validated `biomarker_id` association. It preserves
the observation ID, patient, examination, source document and original code.
Unsupported endpoint update fields return HTTP 422.

Changing value shape clears the previous FHIR value. Changing values, references
or catalog associations invalidates affected numeric caches. A censored quantity
has no exact `raw_value`, `normalized_value`, or `relative_score`.

After writing, verify the returned ID and catalog association, value shape,
comparator, unit, reference, source link, and source hash. Read all collection
pages with a stable timestamp/ID ordering; reject repeated IDs or a changed
total. Confirm that unrelated observations and documents remain unchanged.
