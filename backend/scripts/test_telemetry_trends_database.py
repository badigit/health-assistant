"""Read-only PostgreSQL contract tests using an empty synthetic tenant scope."""
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.telemetry_trends import read_telemetry_trends


class DatabaseTrendTest(unittest.IsolatedAsyncioTestCase):
    async def test_interval_parameters_use_the_postgres_text_codec(self):
        definition=SimpleNamespace(slug='telemetry-contract-test',id='test',is_telemetry=True,
            meta_data=None,value_type='quantity',name='test',aliases=[],preferred_unit_symbol='count',info=None)
        at=datetime(2015,1,1,tzinfo=timezone.utc)
        async with AsyncSessionLocal() as db:
            await db.execute(text('SET LOCAL statement_timeout=5000'))
            for bucket in ['1 minute','1 hour','1 day','1 week','1 month']:
                result=await read_telemetry_trends(db,'11111111-1111-4111-8111-111111111111',
                    '22222222-2222-4222-8222-222222222222',[definition],None,at,at,bucket,'Europe/Moscow')
                self.assertEqual(result,{})
            await db.rollback()


if __name__=='__main__': unittest.main()
