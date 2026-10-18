import unittest
from uuid import uuid4

from app.schemas.examination import ExaminationResponse


class ExaminationObservationValuesTest(unittest.TestCase):
    def test_response_preserves_all_value_shapes(self):
        coded = {'coding': [{'system': 'urn:test', 'code': 'NEG', 'display': 'Negative'}]}
        response = ExaminationResponse.model_validate({
            'id': uuid4(),
            'observations': [
                {'id': uuid4(), 'status': 'final', 'code': {'text': 'Qualitative'}, 'value_codeable_concept': coded},
                {'id': uuid4(), 'status': 'preliminary', 'code': {'text': 'Microscopy'}, 'value_string': '0–2 in field of view'},
                {'id': uuid4(), 'status': 'final', 'code': {'text': 'Quantity'}, 'value_quantity': {'value': 0, 'unit': '1'}, 'interpretation': [{'text': 'L'}]},
            ],
        }).model_dump(mode='json')
        rows = response['observations']
        self.assertEqual(rows[0]['value_codeable_concept'], coded)
        self.assertEqual(rows[1]['value_string'], '0–2 in field of view')
        self.assertEqual(rows[1]['status'], 'preliminary')
        self.assertEqual(rows[2]['value_quantity']['value'], 0)
        self.assertEqual(rows[2]['interpretation'], [{'text': 'L'}])


if __name__ == '__main__':
    unittest.main()
