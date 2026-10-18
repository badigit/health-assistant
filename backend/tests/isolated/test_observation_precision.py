import unittest
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.fhir.patient import Observation
from app.models.biomarker_model import BiomarkerDefinition
from app.models.enums import BiomarkerValueType
from app.services import fhir_service
from app.services.observation_precision import is_censored, validate_quantity, quantity_display
from app.services.observation_value_validator import InvalidObservationValue


class QuantityTests(unittest.TestCase):
    def test_all_supported_comparators_preserve_bounds(self):
        for comparator in ('<', '<=', '>', '>='):
            q = {'value': 7, 'unit': 'mg/L', 'comparator': comparator}
            validate_quantity(q)
            o = SimpleNamespace(value_quantity=q, value_string=None)
            self.assertTrue(is_censored(o))
            self.assertEqual(quantity_display(o), comparator + '7')

    def test_invalid_numbers_and_comparators_are_rejected(self):
        for q in ({'value': float('nan')}, {'value': True}, {'value': '7'}, {'value': 7, 'comparator': '~'}):
            with self.assertRaises(InvalidObservationValue):
                validate_quantity(q)

    def test_state_projection_is_not_a_censored_quantity(self):
        self.assertFalse(is_censored(SimpleNamespace(value_codeable_concept={'text': 'Negative'})))


class UpdateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant = uuid4()
        self.marker = BiomarkerDefinition(id=uuid4(), tenant_id=self.tenant, slug='test-quantity', name='Quantity', value_type=BiomarkerValueType.QUANTITY)
        self.obs = Observation(id=uuid4(), tenant_id=self.tenant, status='final', subject={'reference': f'Patient/{uuid4()}'}, code={'text': 'Original source label'}, effective_datetime=datetime.now(timezone.utc), value_quantity={'value': 12, 'unit': 'mg/L'}, raw_value=12, normalized_value=24, relative_score=2, lab_reference_range={'min': 0, 'max': 10})
        self.session = MagicMock()
        self.session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: self.obs))
        self.session.get = AsyncMock(return_value=self.marker)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.__aenter__ = AsyncMock(return_value=self.session)
        self.session.__aexit__ = AsyncMock(return_value=False)

    async def update(self, data):
        with patch.object(fhir_service, 'DATABASE_AVAILABLE', True), patch.object(fhir_service, 'AsyncSessionLocal', return_value=self.session):
            return await fhir_service.update_observation(self.obs.id, data, self.tenant)

    async def test_reference_patch_roundtrips_and_invalidates_cached_score(self):
        refs = [{'low': {'value': 0, 'unit': 'mg/L'}, 'high': {'value': 15, 'unit': 'mg/L'}, 'text': '0–15 mg/L'}]
        result = await self.update({'reference_range': refs})
        self.assertEqual(result.reference_range, refs)
        self.assertIsNone(result.lab_reference_range)
        self.assertIsNone(result.relative_score)
        self.assertEqual(result.value_quantity['value'], 12)

    async def test_relink_preserves_identity_and_revalidates_value(self):
        original_id, original_code = self.obs.id, self.obs.code
        result = await self.update({'biomarker_id': str(self.marker.id)})
        self.assertEqual(result.id, original_id)
        self.assertEqual(result.code, original_code)
        self.assertEqual(result.biomarker_id, self.marker.id)
        self.assertIsNone(result.normalized_value)

    async def test_other_tenant_catalog_is_rejected_before_commit(self):
        self.marker.tenant_id = uuid4()
        with self.assertRaises(InvalidObservationValue):
            await self.update({'biomarker_id': str(self.marker.id)})
        self.session.commit.assert_not_awaited()

    async def test_text_to_bound_clears_text_and_numeric_caches(self):
        self.obs.value_quantity = None
        self.obs.value_string = '<7 mg/L'
        result = await self.update({'value_quantity': {'value': 7, 'unit': 'mg/L', 'comparator': '<'}})
        self.assertIsNone(result.value_string)
        self.assertIsNone(result.raw_value)
        self.assertIsNone(result.normalized_value)
        self.assertIsNone(result.relative_score)
        self.assertEqual(result.to_fhir_dict()['valueQuantity']['comparator'], '<')

    async def test_exact_zero_replaces_old_value_without_stale_normalization(self):
        result = await self.update({'value_quantity': {'value': 0, 'unit': 'mg/L'}})
        self.assertEqual(result.raw_value, 0)
        self.assertIsNone(result.normalized_value)

    async def test_text_only_update_is_not_silently_ignored(self):
        result = await self.update({'value_string': '0–2 per field'})
        self.assertEqual(result.value_string, '0–2 per field')
        self.assertIsNone(result.value_quantity)
        self.assertIsNone(result.raw_value)


if __name__ == '__main__':
    unittest.main()
