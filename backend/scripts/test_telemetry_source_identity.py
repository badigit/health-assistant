"""Run with python -m unittest scripts.test_telemetry_source_identity (no test DB)."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

from sqlalchemy.dialects import postgresql

from app.schemas.telemetry import TelemetryDataPoint
from app.services.telemetry_service import upload_telemetry_data


class SourceIdentityTest(unittest.IsolatedAsyncioTestCase):
    async def insert_id(self, tenant="11111111-1111-4111-8111-111111111111", **changes):
        point = dict(timestamp=datetime(2015, 1, 1, tzinfo=timezone.utc),
                     slug="heart-rate", value=70.5, unit="bpm", source_id="a" * 64,
                     patient_id=UUID("22222222-2222-4222-8222-222222222222"))
        point.update(changes)
        db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(rowcount=1)),
                             commit=AsyncMock(), rollback=AsyncMock())
        await upload_telemetry_data(db, "watch", [TelemetryDataPoint(**point)], tenant)
        statement = db.execute.call_args.args[0]
        values = statement.compile(dialect=postgresql.dialect()).params
        self.assertIn("ON CONFLICT", str(statement))
        db.commit.assert_awaited_once()
        return values.get("id_m0")

    async def test_retry_and_source_isolation(self):
        first = await self.insert_id()
        self.assertIsNotNone(first)
        self.assertEqual(first, await self.insert_id())
        self.assertEqual(first, await self.insert_id(
            start_timestamp=datetime(2015, 1, 1, tzinfo=timezone.utc), source_name='Watch'))
        self.assertNotEqual(first, await self.insert_id(source_id="b" * 64))
        self.assertNotEqual(first, await self.insert_id(tenant="33333333-3333-4333-8333-333333333333"))
        self.assertNotEqual(first, await self.insert_id(patient_id=UUID("44444444-4444-4444-8444-444444444444")))
        self.assertNotEqual(first, await self.insert_id(value=71.5))

    def test_invalid_source_rejected(self):
        with self.assertRaises(ValueError):
            TelemetryDataPoint(timestamp=datetime.now(timezone.utc), slug="heart-rate",
                               value=70, source_id="not-a-sha256")

    def test_reversed_and_naive_intervals_rejected(self):
        for start in [datetime(2015, 1, 2, tzinfo=timezone.utc), datetime(2015, 1, 1)]:
            with self.assertRaises(ValueError):
                TelemetryDataPoint(timestamp=datetime(2015, 1, 1, tzinfo=timezone.utc),
                                   start_timestamp=start, slug='steps', value=10)


if __name__ == "__main__":
    unittest.main()
