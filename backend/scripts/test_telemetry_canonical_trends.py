"""Canonical telemetry read tests with a synthetic, isolated database boundary."""
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from app.services.telemetry_trends import read_telemetry_trends


def definition(slug, identity, telemetry=False, meta=None):
    return SimpleNamespace(slug=slug,id=identity,is_telemetry=telemetry,meta_data=meta,
                           value_type='quantity',name=slug,aliases=[],preferred_unit_symbol='cm',info=None)


class CanonicalTrendTest(unittest.IsolatedAsyncioTestCase):
    async def test_source_and_target_filters_share_identity_and_convert_height(self):
        source = definition('apple-health-height','source',True,{'canonical_slug':'height','canonical_unit_multiplier':100})
        target = definition('height','target')
        at = datetime(2026,1,1,tzinfo=timezone.utc)
        rows = [{'slug':source.slug,'device_id':'watch','bucket':at,'mean':1.8,'high':1.8,'low':1.8,
                 'latest':1.8,'latest_at':at,'source':'Watch','samples':1}]
        for requested in ['height','apple-health-height','target','source']:
            db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(mappings=lambda:rows)))
            result = await read_telemetry_trends(db,'tenant','patient',[source,target],requested,at,at,'1 day','UTC')
            self.assertEqual(list(result), ['height'])
            point = result['height'][0]
            self.assertEqual((point['value'],point['biomarker_id'],point['status']), (180,'target','Unknown'))
            statement,params = db.execute.call_args.args
            self.assertIn('tenant_id=CAST(:tenant AS uuid)',str(statement))
            self.assertIn('patient_id=CAST(:patient AS uuid)',str(statement))
            self.assertEqual((params['tenant'],params['patient']),('tenant','patient'))

    async def test_foreign_or_missing_target_does_not_change_identity(self):
        source = definition('apple-health-height','source',True,{'canonical_slug':'missing'})
        at = datetime(2026,1,1,tzinfo=timezone.utc)
        db = SimpleNamespace(execute=AsyncMock())
        result = await read_telemetry_trends(db,'tenant','patient',[source],'missing',at,at,'1 day','UTC')
        self.assertEqual(result,{})
        db.execute.assert_not_awaited()


if __name__ == '__main__': unittest.main()
