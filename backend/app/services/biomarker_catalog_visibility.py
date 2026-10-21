"""Keep linked source definitions available without offering duplicate metrics."""

from sqlalchemy import text


CANONICAL_CATALOG_SQL = """NOT EXISTS (
    SELECT 1 FROM biomarker_definitions canonical_target
    WHERE canonical_target.slug = source.meta_data->>'canonical_slug'
      AND canonical_target.id <> source.id
      AND (canonical_target.tenant_id IS NULL OR canonical_target.tenant_id = :tenant_id)
      AND COALESCE(canonical_target.meta_data->>'canonical_slug', '') = ''
)"""


def canonical_catalog_filter(tenant_id):
    """Hide an alias only when its terminal canonical target is visible."""
    return text(CANONICAL_CATALOG_SQL.replace('source.', 'biomarker_definitions.')).bindparams(
        tenant_id=tenant_id
    )
