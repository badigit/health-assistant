"""Canonical wearable metrics and source-aware interval reconciliation."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import heapq
from zoneinfo import ZoneInfo


# source suffix: canonical slug, display name, unit, multiplier, aggregation
APPLE_METRICS = {
    'heart-rate': ('heart-rate', 'Частота сердечных сокращений', '/min', 1, 'mean'),
    'resting-heart-rate': ('resting-heart-rate', 'Пульс в покое', '/min', 1, 'mean'),
    'walking-heart-rate': ('walking-heart-rate', 'Средний пульс при ходьбе', '/min', 1, 'mean'),
    'heart-rate-recovery': ('heart-rate-recovery', 'Восстановление пульса за минуту', '/min', 1, 'mean'),
    'hrv-sdnn': ('hrv-sdnn', 'Вариабельность пульса SDNN', 'ms', 1, 'mean'),
    'steps': ('steps', 'Шаги за день', 'count', 1, 'total'),
    'active-energy': ('active-energy', 'Активная энергия за день', 'kcal', 1, 'total'),
    'resting-energy': ('resting-energy', 'Энергия покоя за день', 'kcal', 1, 'total'),
    'flights-climbed': ('flights-climbed', 'Подъёмы по лестнице за день', 'count', 1, 'total'),
    'exercise-time': ('exercise-time', 'Время упражнений за день', 'min', 1, 'total'),
    'walking-running-distance': ('walking-running-distance', 'Расстояние ходьбы и бега за день', 'm', 1, 'total'),
    'vo2-max': ('vo2-max', 'Максимальное потребление кислорода', 'mL/kg/min', 1, 'latest'),
    'weight': ('weight', 'Вес', 'kg', 1, 'latest'),
    'lean-body-mass': ('lean-body-mass', 'Безжировая масса тела', 'kg', 1, 'latest'),
    'height': ('height', 'Рост', 'cm', 100, 'latest'),
    'waist-circumference': ('waist-circumference', 'Окружность талии', 'cm', 100, 'latest'),
    'bmi': ('bmi', 'Индекс массы тела', 'kg/m2', 1, 'latest'),
    'body-fat': ('body-fat', 'Доля жира', '%', 1, 'latest'),
    'spo2': ('oxygen-saturation', 'Сатурация кислорода (SpO2)', '%', 1, 'mean'),
    'afib-burden': ('afib-burden', 'Нагрузка фибрилляцией предсердий', '%', 1, 'mean'),
    'respiratory-rate': ('respiratory-rate', 'Частота дыхания', '/min', 1, 'mean'),
    'systolic-bp': ('systolic-bp', 'Систолическое артериальное давление', 'mm[Hg]', 1, 'latest'),
    'diastolic-bp': ('diastolic-bp', 'Диастолическое артериальное давление', 'mm[Hg]', 1, 'latest'),
    'glucose': ('glucose-unspecified', 'Глюкоза', 'mmol/L', 1, 'latest'),
    'temperature': ('body-temperature', 'Температура тела', 'Cel', 1, 'latest'),
    'sleep-breathing-disturbances': ('sleep-breathing-disturbances', 'Нарушения дыхания во сне', '/h', 1, 'mean'),
    'workout-duration': ('workout-duration', 'Длительность тренировок за день', 'min', 1, 'total'),
    'workout-distance': ('workout-distance', 'Расстояние тренировок за день', 'm', 1, 'total'),
    'workout-energy': ('workout-energy', 'Энергия тренировок за день', 'kcal', 1, 'total'),
    'sleep-inbed': ('sleep-in-bed', 'Время в постели', 'min', 1, 'sleep'),
    'sleep-awake': ('sleep-awake', 'Бодрствование во время сна', 'min', 1, 'sleep'),
    'sleep-asleepcore': ('sleep-core', 'Сон: базовая фаза', 'min', 1, 'sleep'),
    'sleep-asleepdeep': ('sleep-deep', 'Сон: глубокая фаза', 'min', 1, 'sleep'),
    'sleep-asleeprem': ('sleep-rem', 'Сон: фаза REM', 'min', 1, 'sleep'),
    'sleep-asleepunspecified': ('sleep-unspecified', 'Сон: фаза не определена', 'min', 1, 'sleep'),
}
CANONICAL_MODES = {spec[0]: spec[4] for spec in APPLE_METRICS.values()}
CANONICAL_MODES['sleep-duration'] = 'sleep'
ASLEEP = {'sleep-core', 'sleep-deep', 'sleep-rem', 'sleep-unspecified'}
LEGACY_SLUGS = {
    'systolic-blood-pressure': 'systolic-bp',
    'diastolic-blood-pressure': 'diastolic-bp',
    'body-mass-index': 'bmi',
}


def source_priority(name):
    """Prefer wearable readings, then phone, then imported copies."""
    label = (name or '').lower()
    if 'import' in label:
        return 10
    if 'watch' in label:
        return 100
    if 'phone' in label:
        return 80
    return 50


@dataclass(slots=True)
class Interval:
    start: datetime
    end: datetime
    value: float
    source: str
    priority: int
    identity: str
    metric: str


def reconcile_daily(intervals, zone, *, sleep=False, start=None, end=None):
    """Split source-prioritized, non-overlapping intervals into local days.

    Quantity counts are allocated uniformly inside their original interval.
    Clipped quantities are marked estimated. Sleep is the union of intervals;
    awake blocks lower-priority asleep records, and in-bed is kept separate.
    """
    tz = ZoneInfo(zone)
    totals = defaultdict(float)
    estimated = set()
    events = []
    active = set()
    heap = []
    for index, row in enumerate(intervals):
        left, right = row.start, row.end
        if right < left or (sleep and right == left):
            continue
        if start:
            left = max(left, start)
        if end:
            right = min(right, end)
        if right < left:
            continue
        if right == left:
            if row.start == row.end and (not start or right >= start) and (not end or right <= end):
                events.append((right, 0, index))
            continue
        events.extend(((left, 1, index), (right, -1, index)))
    events.sort()

    def rank(index):
        row = intervals[index]
        specificity = 0 if row.metric == 'sleep-unspecified' else 1
        return (-row.priority, -specificity, (row.end-row.start).total_seconds(), row.source, row.identity, index)

    def accumulate(left, right, row, instant=False):
        while left < right or instant:
            local = left.astimezone(tz)
            boundary = datetime.combine(local.date()+timedelta(days=1), datetime.min.time(), tz).astimezone(timezone.utc)
            stop = min(right, boundary)
            key = (row.metric, local.date().isoformat())
            duration = (row.end-row.start).total_seconds()
            quantity = row.value if instant else ((stop-left).total_seconds()/60 if sleep else row.value*(stop-left).total_seconds()/duration)
            totals[key] += quantity
            if not sleep and not instant and (left != row.start or stop != row.end):
                estimated.add(key)
            if sleep and row.metric in ASLEEP:
                totals[('sleep-duration', key[1])] += quantity
            if instant:
                break
            left = stop

    previous = None
    position = 0
    while position < len(events):
        at = events[position][0]
        while heap and heap[0][-1] not in active:
            heapq.heappop(heap)
        if previous is not None and at > previous and heap:
            accumulate(previous, at, intervals[heap[0][-1]])
        instant = []
        while position < len(events) and events[position][0] == at:
            _, kind, index = events[position]
            if kind == -1:
                active.discard(index)
            elif kind == 1:
                active.add(index)
                heapq.heappush(heap, rank(index))
            else:
                instant.append(index)
            position += 1
        if instant:
            best = min(instant, key=rank)
            while heap and heap[0][-1] not in active:
                heapq.heappop(heap)
            if not heap or rank(best) < heap[0]:
                accumulate(at, at, intervals[best], instant=True)
        previous = at
    return [{'metric': metric, 'date': datetime.fromisoformat(day).replace(tzinfo=tz).isoformat(),
             'value': round(value) if metric in {'steps', 'flights-climbed'} else round(value, 2),
             'estimated': (metric, day) in estimated}
            for (metric, day), value in sorted(totals.items())]
