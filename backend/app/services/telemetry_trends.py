"""Read canonical telemetry without moving or duplicating source measurements."""
from collections import defaultdict
from datetime import timedelta
from sqlalchemy import bindparam, text
from app.services.telemetry_semantics import (
    CANONICAL_MODES, LEGACY_SLUGS, Interval, reconcile_daily, source_priority,
)


def normalized_key(value):
    return LEGACY_SLUGS.get(value.lower().replace(' ', '-'), value.lower().replace(' ', '-'))


async def read_telemetry_trends(db, tenant_id, patient_id, definitions, requested,
                                start, end, bucket, zone, clinical_groups=None):
    """Return source-attributed series keyed by canonical catalog identity."""
    by_slug = {item.slug: item for item in definitions}
    links = {}
    for item in definitions:
        if not item.is_telemetry:
            continue
        meta = item.meta_data or {}
        target = by_slug.get(meta.get('canonical_slug'), item)
        if target.value_type != item.value_type:
            continue
        links[item.slug] = (target, float(meta.get('canonical_unit_multiplier', 1)))
    wanted = {normalized_key(key.strip()) for key in requested.split(',')} if requested else set()

    def matches(source, target):
        if not wanted:
            return True
        keys = {normalized_key(k) for k in (
            source, by_slug[source].name, str(by_slug[source].id),
            target.slug, target.name, str(target.id), *(target.aliases or []))}
        keys.update(normalized_key(k) for k in ((by_slug[source].aliases or [])))
        return bool(keys & wanted)

    selected = {slug: spec for slug, spec in links.items() if matches(slug, spec[0])}
    want_sleep_total = not wanted or 'sleep-duration' in wanted or (
        'sleep-duration' in by_slug and str(by_slug['sleep-duration'].id) in wanted)
    sleep_selected = want_sleep_total or any(CANONICAL_MODES.get(t.slug) == 'sleep' for t, _ in selected.values())
    if sleep_selected:
        selected.update({slug: spec for slug, spec in links.items() if CANONICAL_MODES.get(spec[0].slug) == 'sleep'})
    if not selected:
        return {}
    await db.execute(text('SET LOCAL max_parallel_workers_per_gather=0'))
    output = defaultdict(list)

    def point(target, at, value, source=None, **extra):
        return dict(date=at, value=value, unit=getattr(target, 'preferred_unit_symbol', '') or '',
                    name=target.name, status='Unknown', biomarker_id=str(target.id),
                    aliases=target.aliases or [],
                    info=('Дневной итог за календарные сутки в выбранном часовом поясе. '
                          'Пересечения источников исключены; Watch имеет приоритет перед телефоном, импорт — последним. '
                          'Знак ≈ обозначает пропорциональное распределение части интервала.'
                          if CANONICAL_MODES.get(target.slug) in {'total', 'sleep'} else target.info),
                    source_slugs=[slug for slug, spec in links.items() if spec[0].slug == target.slug],
                    source_type='telemetry', source_name=source or 'Устройства',
                    source_id=None, source_category='telemetry', technical_category='telemetry',
                    clinical_groups=(clinical_groups or {}).get(target.id) or ['Данные устройств'], examination_id=None, examination_name=None,
                    reference_range_min=None, reference_range_max=None, reference_range_text='--', **extra)

    params = {'tenant': tenant_id, 'start': start, 'end': end, 'zone': zone}
    patient_clause = ' AND patient_id=CAST(:patient AS uuid)' if patient_id else ''
    if patient_id:
        params['patient'] = patient_id
    base = (' FROM telemetry_data WHERE tenant_id=CAST(:tenant AS uuid) '
            'AND timestamp>=:start AND timestamp<=:end AND slug IN :slugs' + patient_clause)
    intervals = {slug: spec for slug, spec in selected.items()
                 if CANONICAL_MODES.get(spec[0].slug) in {'total', 'sleep'}}
    gauges = {slug: spec for slug, spec in selected.items() if slug not in intervals}
    if gauges:
        statement = text(
            "SELECT slug,device_id,time_bucket(CAST(CAST(:bucket AS text) AS interval),timestamp,CAST(:zone AS text)) AS bucket,"
            "AVG(value) AS mean,MAX(value) AS high,MIN(value) AS low,"
            "last(value,timestamp) AS latest,MAX(timestamp) AS latest_at,"
            "last(source_name,timestamp) AS source,count(*) AS samples" + base +
            ' GROUP BY slug,device_id,3 ORDER BY 3'
        ).bindparams(bindparam('slugs', expanding=True))
        result = await db.execute(statement, dict(params, slugs=list(gauges), bucket=bucket))
        chosen = {}
        for row in result.mappings():
            target, factor = gauges[row['slug']]
            key = (target.slug, row['bucket'])
            candidate = (source_priority(row['source']), row['latest_at'], row['device_id'])
            if key in chosen and chosen[key][0] >= candidate:
                continue
            mode = CANONICAL_MODES.get(target.slug, 'mean')
            value = row['latest'] if mode == 'latest' else row['mean']
            chosen[key] = (candidate, point(target, row['bucket'].isoformat(), round(value*factor, 4),
                row['source'] or row['device_id'], latest_value=row['latest']*factor,
                latest_date=row['latest_at'].isoformat(), max_value=row['high']*factor,
                min_value=row['low']*factor, sample_count=row['samples'], source_slug=row['slug'],
                aggregation=mode))
        for (slug, _), (_, value) in chosen.items():
            output[slug].append(value)
    if intervals:
        interval_base = base.replace('timestamp<=:end', 'COALESCE(start_timestamp,timestamp)<=:end')
        statement = text('SELECT id,slug,timestamp,start_timestamp,value,device_id,source_name' + interval_base).bindparams(
            bindparam('slugs', expanding=True))
        result = await db.stream(statement.execution_options(yield_per=5000), dict(params, slugs=list(intervals)))
        groups = defaultdict(list)
        targets = {}
        missing = defaultdict(int)
        async for row in result.mappings():
            target, factor = intervals[row['slug']]
            targets[target.slug] = target
            left = row['start_timestamp']
            if left is None:
                if CANONICAL_MODES.get(target.slug) == 'sleep':
                    left = row['timestamp']-timedelta(minutes=row['value']*factor)
                else:
                    missing[target.slug] += 1
                    continue
            if left > row['timestamp']:
                missing[target.slug] += 1
                continue
            group = 'sleep' if CANONICAL_MODES.get(target.slug) == 'sleep' and target.slug != 'sleep-in-bed' else target.slug
            groups[group].append(Interval(left, row['timestamp'], row['value']*factor,
                row['device_id'], source_priority(row['source_name']), str(row['id']), target.slug))
        for group, values in groups.items():
            is_sleep = group == 'sleep' or group == 'sleep-in-bed'
            totals = reconcile_daily(values, zone, sleep=is_sleep, start=start, end=end)
            for total in totals:
                slug = total.pop('metric')
                if slug == 'sleep-duration':
                    if not want_sleep_total or slug not in by_slug:
                        continue
                    target = by_slug[slug]
                else:
                    target = targets[slug]
                    source_slug = next(s for s, spec in intervals.items() if spec[0].slug == slug)
                    if not matches(source_slug, target):
                        continue
                output[slug].append(point(target, total.pop('date'), total.pop('value'),
                    aggregation='daily_total', missing_intervals=missing[slug], **total))
    return dict(output)
