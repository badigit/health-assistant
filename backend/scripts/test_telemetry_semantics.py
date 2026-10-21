"""Interval acceptance tests; fixtures contain synthetic measurements only."""
from datetime import datetime, timedelta, timezone
import unittest
from app.services.telemetry_semantics import APPLE_METRICS, Interval, reconcile_daily, source_priority


def interval(start, end, value, source='Watch', metric='steps', identity=None):
    left, right = (datetime.fromisoformat(v.replace('Z', '+00:00')) for v in (start, end))
    return Interval(left, right, value, source, source_priority(source), identity or str(value), metric)


class SemanticsTest(unittest.TestCase):
    def test_localized_watch_source_has_wearable_priority(self):
        self.assertGreater(source_priority('Часы'), source_priority('iPhone'))
        self.assertLess(source_priority('Импорт здоровья'), source_priority('iPhone'))

    def test_all_35_source_metrics_have_distinct_specific_targets(self):
        self.assertEqual(len(APPLE_METRICS), 35)
        self.assertEqual(len({spec[0] for spec in APPLE_METRICS.values()}), 35)
        self.assertEqual(APPLE_METRICS['glucose'][0], 'glucose-unspecified')
        self.assertEqual(APPLE_METRICS['hrv-sdnn'][0], 'hrv-sdnn')
        self.assertEqual(APPLE_METRICS['height'][3], 100)

    def test_watch_phone_overlap_and_uncovered_phone_segment(self):
        rows = [interval('2026-01-01T10:00Z', '2026-01-01T11:00Z', 600),
                interval('2026-01-01T10:30Z', '2026-01-01T11:30Z', 1200, 'iPhone'),
                interval('2026-01-01T10:00Z', '2026-01-01T11:00Z', 600, 'Health Import')]
        result = reconcile_daily(rows, 'UTC')
        self.assertEqual(result[0]['value'], 1200)
        self.assertTrue(result[0]['estimated'])

    def test_imported_duplicate_cannot_double_the_total(self):
        rows = [interval('2026-01-01T10:00Z', '2026-01-01T11:00Z', 500),
                interval('2026-01-01T10:00Z', '2026-01-01T11:00Z', 500, 'Health Import')]
        self.assertEqual(reconcile_daily(rows, 'UTC')[0]['value'], 500)

    def test_different_day_intervals_are_summed_not_averaged(self):
        rows = [interval('2026-01-01T10:00Z', '2026-01-01T11:00Z', 500),
                interval('2026-01-01T12:00Z', '2026-01-01T13:00Z', 800)]
        self.assertEqual(reconcile_daily(rows, 'UTC')[0]['value'], 1300)

    def test_midnight_uses_requested_zone_and_preserves_total(self):
        rows = [interval('2026-01-01T20:30Z', '2026-01-01T21:30Z', 600)]
        values = reconcile_daily(rows, 'Europe/Moscow')
        self.assertEqual([r['value'] for r in values], [300, 300])
        self.assertEqual([r['date'][:10] for r in values], ['2026-01-01', '2026-01-02'])

    def test_dst_boundary_is_real_elapsed_time(self):
        rows = [interval('2026-03-29T00:00Z', '2026-03-29T03:00Z', 180)]
        self.assertEqual(reconcile_daily(rows, 'Europe/Berlin')[0]['value'], 180)

    def test_sleep_union_with_awake_and_unspecified_fallback(self):
        rows = [interval('2026-01-01T00:00Z', '2026-01-01T01:00Z', 60, metric='sleep-core'),
                interval('2026-01-01T01:00Z', '2026-01-01T01:15Z', 15, metric='sleep-awake'),
                interval('2026-01-01T00:00Z', '2026-01-01T02:00Z', 120, 'iPhone', 'sleep-unspecified')]
        totals = {r['metric']: r['value'] for r in reconcile_daily(rows, 'UTC', sleep=True)}
        self.assertEqual(totals['sleep-duration'], 105)
        self.assertEqual(totals['sleep-core'], 60)
        self.assertEqual(totals['sleep-unspecified'], 45)
        self.assertEqual(totals['sleep-awake'], 15)

    def test_sleep_same_source_nested_intervals_do_not_double(self):
        rows = [interval('2026-01-01T00:00Z', '2026-01-01T02:00Z', 120, metric='sleep-unspecified'),
                interval('2026-01-01T00:30Z', '2026-01-01T01:30Z', 60, metric='sleep-deep')]
        totals = {r['metric']: r['value'] for r in reconcile_daily(rows, 'UTC', sleep=True)}
        self.assertEqual(totals['sleep-duration'], 120)
        self.assertEqual(totals['sleep-deep'], 60)

    def test_point_quantities_are_not_dropped(self):
        rows = [interval('2026-01-01T00:00Z', '2026-01-01T00:00Z', 12)]
        self.assertEqual(reconcile_daily(rows, 'UTC')[0]['value'], 12)

    def test_clipped_time_window_is_marked_estimated(self):
        rows = [interval('2026-01-01T00:00Z', '2026-01-01T02:00Z', 120)]
        result = reconcile_daily(rows, 'UTC', start=datetime(2026,1,1,1,tzinfo=timezone.utc))
        self.assertEqual(result[0]['value'], 60)
        self.assertTrue(result[0]['estimated'])


if __name__ == '__main__':
    unittest.main()
