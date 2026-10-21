"""Exercise catalog source visibility on isolated temporary PostgreSQL tables."""
import unittest
from uuid import uuid4

from sqlalchemy import text

from app.core.database import AsyncSessionLocal, engine
from app.services.biomarker_catalog_visibility import CANONICAL_CATALOG_SQL, canonical_catalog_filter
from app.services.catalog_search_service import _specs_by_type, _hybrid_search_one


class CatalogSourceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await engine.dispose()

    async def test_visibility_search_and_tenant_boundaries(self):
        tenant, foreign = uuid4(), uuid4()
        async with AsyncSessionLocal() as db:
            await db.execute(text('SET LOCAL statement_timeout=5000'))
            await db.execute(text('CREATE TEMP TABLE biomarker_definitions (LIKE public.biomarker_definitions INCLUDING DEFAULTS) ON COMMIT DROP'))
            await db.execute(text('SET LOCAL search_path=pg_temp,public'))
            definitions = [
                ('target', None, None),
                ('linked', None, 'target'),
                ('missing', None, 'absent'),
                ('empty', None, ''),
                ('foreign-target', foreign, None),
                ('foreign-link', None, 'foreign-target'),
                ('own-target', tenant, None),
                ('own-link', tenant, 'own-target'),
                ('self-link', None, 'self-link'),
                ('chain', None, 'linked'),
            ]
            for slug, owner, canonical in definitions:
                await db.execute(text('''INSERT INTO biomarker_definitions
                    (id,slug,name,code,coding_system,tenant_id,is_telemetry,scope,version,aliases,meta_data)
                    VALUES (:id,:slug,:name,:slug,'CUSTOM',:owner,false,'system',1,'["source-catalog-test"]',
                    CASE WHEN CAST(:canonical AS text) IS NULL THEN NULL
                    ELSE jsonb_build_object('canonical_slug',CAST(:canonical AS text)) END)'''),
                    dict(id=uuid4(),slug=slug,name='source-catalog-test '+slug,owner=owner,canonical=canonical))
            condition = CANONICAL_CATALOG_SQL.replace('source.', 't.')
            rows = (await db.execute(text('SELECT slug FROM biomarker_definitions t WHERE '
                '(tenant_id IS NULL OR tenant_id=:tenant_id) AND '+condition), {'tenant_id':tenant})).scalars().all()
            self.assertEqual(set(rows), {'target','missing','empty','foreign-link','own-target','self-link','chain'})
            from sqlalchemy import select, or_
            from app.models.biomarker_model import BiomarkerDefinition
            orm_rows = (await db.execute(select(BiomarkerDefinition.slug).where(
                or_(BiomarkerDefinition.tenant_id.is_(None), BiomarkerDefinition.tenant_id==tenant),
                canonical_catalog_filter(tenant)))).scalars().all()
            self.assertEqual(set(orm_rows),set(rows))
            hits = await _hybrid_search_one(db,_specs_by_type()['biomarker'],'source-catalog-test',tenant,limit=100)
            self.assertEqual({h.label.removeprefix('source-catalog-test ') for h in hits},set(rows))
            from app.catalogs.adapters import BiomarkerCatalogAdapter
            adapter = BiomarkerCatalogAdapter()
            page = await adapter.list(db,tenant,limit=2,offset=0)
            self.assertEqual(page['total'],len(rows))
            self.assertEqual(len(page['items']),2)
            rest = await adapter.list(db,tenant,limit=100,offset=2)
            self.assertEqual({i['slug'] for i in page['items']+rest['items']},set(rows))
            all_sources = await adapter.list(db,tenant,include_sources=True)
            self.assertEqual(all_sources['total'],9)
            source = next(i for i in all_sources['items'] if i['slug']=='linked')
            self.assertEqual((await adapter.get(db,tenant,source['id']))['slug'],'linked')
            await db.execute(text("UPDATE biomarker_definitions SET aliases='[\"unique-source-alias\"]' WHERE slug='target'"))
            found = await adapter.list(db,tenant,search='unique-source-alias')
            self.assertEqual([i['slug'] for i in found['items']],['target'])
            await db.rollback()


if __name__ == '__main__': unittest.main()
