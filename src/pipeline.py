"""Real Criteo campaign reporting, with an offline aggregate rebuild path."""
from __future__ import annotations
import argparse
import csv
import gzip
import json
import sqlite3
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from fetch_data import REVISION, SHA256, URL, digest

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / 'data/derived'
SCALE = 10**12
FIELDS = ['day','campaign','impressions','clicks','conversions','post_click_conversions','cost_scaled']
REQUIRED = ['timestamp','campaign','conversion','conversion_timestamp','conversion_id','attribution','click','cost']
SOURCE_PAGE = 'https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/'

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def write_csv(path, rows, fields=None):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def ingest(records):
    """Stream source rows; retain campaign/day totals and one allocation per sale.

    Each (conversion ID, conversion timestamp) key is counted once globally. Prefer the most recent observed
    clicked, credited impression; otherwise the most recent credited impression.
    This is an explicit project allocation rule over subsampled data, not proof
    of the platform's exact credited touchpoint. No user identifiers are retained.
    """
    groups, allocations, rejected = {}, {}, []
    reasons = Counter()
    source_rows = accepted = credited_impressions = nonmonotonic = 0
    previous_timestamp = -1
    observed_conversion_keys = set()
    conversion_id_times = {}
    reused_conversion_ids = set()
    conflicting_campaign_ids = set()
    min_timestamp, max_timestamp = None, None
    for line, raw in enumerate(records, 2):
        source_rows += 1
        try:
            if any(k not in raw for k in REQUIRED):
                raise ValueError('missing_required_field')
            values = {k: int(raw[k]) for k in REQUIRED if k != 'cost'}
            cost = Decimal(raw['cost'])
            if not cost.is_finite() or cost < 0:
                raise ValueError('invalid_cost')
            if values['timestamp'] < 0 or values['campaign'] < 0:
                raise ValueError('invalid_dimension')
            if any(values[k] not in (0, 1) for k in ['conversion','attribution','click']):
                raise ValueError('nonbinary_flag')
            if values['attribution'] > values['conversion']:
                raise ValueError('attribution_without_conversion')
            if values['conversion']:
                if values['conversion_id'] < 0 or values['conversion_timestamp'] < values['timestamp']:
                    raise ValueError('invalid_conversion_metadata')
            elif values['conversion_id'] != -1 or values['conversion_timestamp'] != -1:
                raise ValueError('unexpected_conversion_metadata')
            cost_scaled = int((cost * SCALE).to_integral_value(rounding=ROUND_HALF_EVEN))
        except (ValueError, TypeError, KeyError, InvalidOperation, OverflowError) as exc:
            reason = str(exc) if str(exc) in {'missing_required_field','invalid_cost','invalid_dimension','nonbinary_flag','attribution_without_conversion','invalid_conversion_metadata','unexpected_conversion_metadata'} else 'malformed_value'
            reasons[reason] += 1
            # Record position/reason only; do not publish pseudonymous identifiers.
            rejected.append({'source_line':line,'reason':reason})
            continue
        accepted += 1
        timestamp = values['timestamp']
        nonmonotonic += timestamp < previous_timestamp
        previous_timestamp = timestamp
        min_timestamp = timestamp if min_timestamp is None else min(min_timestamp, timestamp)
        max_timestamp = timestamp if max_timestamp is None else max(max_timestamp, timestamp)
        day, campaign = timestamp // 86400, str(values['campaign'])
        key = day, campaign
        if key not in groups:
            groups[key] = dict(zip(FIELDS, [day,campaign,0,0,0,0,0]))
        group = groups[key]
        group['impressions'] += 1
        group['clicks'] += values['click']
        group['cost_scaled'] += cost_scaled
        if values['conversion']:
            cid, conversion_time = values['conversion_id'], values['conversion_timestamp']
            observed_conversion_keys.add((cid, conversion_time))
            first_time = conversion_id_times.setdefault(cid, conversion_time)
            if first_time != conversion_time:
                reused_conversion_ids.add(cid)
        if values['attribution']:
            credited_impressions += 1
            cid = (values['conversion_id'], values['conversion_timestamp'])
            # Deterministic ties: campaign ID, then source line. No per-user key.
            candidate = (values['click'],timestamp,values['campaign'],line,day,campaign)
            old = allocations.get(cid)
            if old is not None and old[-1] != campaign:
                conflicting_campaign_ids.add(cid)
            if old is None or candidate > old:
                allocations[cid] = candidate
        if source_rows % 2_000_000 == 0:
            print(f'Processed {source_rows:,} source impressions', flush=True)
    for click, _, _, _, day, campaign in allocations.values():
        groups[day,campaign]['conversions'] += 1
        groups[day,campaign]['post_click_conversions'] += click
    rows = [groups[k] for k in sorted(groups)]
    quality = {
        'source_rows': source_rows, 'accepted_rows': accepted,
        'quarantined_rows': len(rejected), 'reasons': dict(reasons),
        'daily_campaign_rows': len(rows), 'campaigns': len({r['campaign'] for r in rows}),
        'observed_days': len({r['day'] for r in rows}),
        'min_timestamp': min_timestamp, 'max_timestamp': max_timestamp,
        'out_of_order_timestamps': nonmonotonic,
        'unique_observed_conversion_ids': len(conversion_id_times),
        'unique_observed_conversion_keys': len(observed_conversion_keys),
        'conversion_ids_with_multiple_timestamps': len(reused_conversion_ids),
        'unique_credited_conversion_ids': len({cid for cid, _ in allocations}),
        'credited_conversion_impressions': credited_impressions,
        'unique_credited_conversions': len(allocations),
        'repeated_credited_conversion_links_collapsed': credited_impressions - len(allocations),
        'credited_conversion_keys_linked_to_multiple_campaigns': len(conflicting_campaign_ids),
        'total_cost_scaled': sum(r['cost_scaled'] for r in rows),
        'total_clicks': sum(r['clicks'] for r in rows),
        'post_click_conversions': sum(r['post_click_conversions'] for r in rows),
    }
    return rows, quality, rejected

def import_source(source):
    actual_hash = digest(source)
    if actual_hash != SHA256:
        raise ValueError('Source checksum mismatch; use the pinned Criteo release')
    with gzip.open(source, 'rt', newline='') as f:
        rows, quality, rejected = ingest(csv.DictReader(f, delimiter='\t'))
    DERIVED.mkdir(parents=True, exist_ok=True)
    write_csv(DERIVED/'campaign_daily.csv', rows, FIELDS)
    write_json(DERIVED/'quality.json', quality)
    write_json(DERIVED/'quarantine.json', rejected)
    write_json(DERIVED/'provenance.json', {
        'dataset': 'Criteo Attribution Modeling for Bidding Dataset',
        'source_url': URL, 'documentation_url': SOURCE_PAGE,
        'source_revision': REVISION, 'source_sha256': actual_hash,
        'source_bytes': source.stat().st_size,
        'coverage': 'Full pinned release; no additional row sampling by this project. Criteo already subsampled the original traffic.',
        'license': 'CC-BY-NC-SA-4.0',
        'cost_scale': SCALE, 'cost_currency': None, 'revenue_available': False,
        'time_basis': 'Floor of relative impression timestamp / 86400; no calendar dates supplied.',
        'conversion_allocation': 'One credited (conversion_id, conversion_timestamp) key globally; prefer latest observed clicked credited impression, otherwise latest observed credited impression. Ties: campaign ID then source row.',
        'published_grain': 'relative_day × campaign_id',
    })
    print(json.dumps(quality, indent=2), flush=True)

def load_derived():
    with (DERIVED/'campaign_daily.csv').open(newline='') as f:
        rows = [{k:(v if k == 'campaign' else int(v)) for k,v in r.items()} for r in csv.DictReader(f)]
    return rows, json.loads((DERIVED/'quality.json').read_text()), json.loads((DERIVED/'provenance.json').read_text())

def validate_derived(rows, quality):
    if not rows:
        raise ValueError('No campaign data')
    keys = set()
    for r in rows:
        key = r['day'],r['campaign']
        if key in keys:
            raise ValueError('Duplicate campaign/day aggregate')
        keys.add(key)
        if min(r[k] for k in FIELDS if k != 'campaign') < 0:
            raise ValueError('Negative aggregate')
        if not r['post_click_conversions'] <= r['clicks'] <= r['impressions']:
            raise ValueError('Invalid post-click funnel')
        if not r['post_click_conversions'] <= r['conversions'] <= r['impressions']:
            raise ValueError('Invalid credited-conversion aggregate')
    checks = {'impressions':'accepted_rows','clicks':'total_clicks','conversions':'unique_credited_conversions','post_click_conversions':'post_click_conversions','cost_scaled':'total_cost_scaled'}
    for field, expected in checks.items():
        if sum(r[field] for r in rows) != quality[expected]:
            raise ValueError(f'Aggregate reconciliation failed: {field}')
    if quality['source_rows'] != quality['accepted_rows'] + quality['quarantined_rows']:
        raise ValueError('Source accounting failed')

def database(rows, path):
    con = sqlite3.connect(path)
    con.execute('DROP TABLE IF EXISTS campaign_daily')
    con.execute('CREATE TABLE campaign_daily (day INTEGER, campaign TEXT, impressions INTEGER, clicks INTEGER, conversions INTEGER, post_click_conversions INTEGER, cost_scaled INTEGER, PRIMARY KEY(day,campaign))')
    con.executemany('INSERT INTO campaign_daily VALUES (?,?,?,?,?,?,?)', [[r[k] for k in FIELDS] for r in rows])
    con.executescript((ROOT/'sql/metrics.sql').read_text())
    con.commit()
    con.row_factory = sqlite3.Row
    return con

def run(output):
    rows, quality, provenance = load_derived()
    validate_derived(rows, quality)
    output.mkdir(parents=True, exist_ok=True)
    con = database(rows, output/'campaigns.sqlite')
    campaigns = [dict(r) for r in con.execute('SELECT * FROM campaign_kpis ORDER BY impressions DESC,campaign')]
    daily = [dict(r) for r in con.execute('SELECT * FROM daily_kpis ORDER BY day')]
    total = dict(con.execute('SELECT * FROM overall_kpis').fetchone())
    write_csv(output/'campaign_daily.csv',rows,FIELDS)
    write_csv(output/'campaign_kpis.csv',campaigns)
    write_csv(output/'daily_kpis.csv',daily)
    write_json(output/'quality.json',quality)
    write_json(output/'provenance.json',provenance)
    write_json(output/'quarantine.json',json.loads((DERIVED/'quarantine.json').read_text()))
    write_json(output/'summary.json', {'quality':quality,'overall':total})
    template = (ROOT/'src/dashboard.html').read_text()
    payload = {'rows':rows,'quality':quality,'provenance':provenance}
    (output/'index.html').write_text(template.replace('__PAYLOAD__', json.dumps(payload,separators=(',',':'))))
    eligible = [r for r in campaigns if r['conversions'] >= 100 and r['clicks'] >= 100]
    candidate = min(eligible, key=lambda r:r['cpa_transformed']) if eligible else None
    comparison = (f"Among campaigns with at least 100 credited conversions and 100 clicks, campaign {candidate['campaign']} has the lowest observed CPA ({candidate['cpa_transformed']:.6f} transformed units). This volume gate is a review heuristic, not a significance test or evidence of incremental effectiveness." if candidate else 'No campaign meets the 100-conversion/100-click review gate.')
    memo = f'''# Real-data campaign business review

## What the full release shows
- {total['impressions']:,} observed impressions across {quality['campaigns']:,} campaigns and {quality['observed_days']} relative day bins.
- {total['clicks']:,} clicks; weighted CTR: {total['ctr']:.2%}.
- {total['conversions']:,} unique Criteo-credited conversion keys (ID + timestamp) after deduplication; {total['post_click_conversions']:,} have an observed clicked credited impression.
- Post-click credited CVR: {total['post_click_cvr']:.2%}. CPA: {total['cpa_transformed']:.6f} transformed cost units per credited conversion.
- {comparison}

## Recommended conversation
1. Ask Customer Success for the advertiser objective, target efficiency, attribution settings and actual cost/revenue exports before treating these comparisons as actionable client economics.
2. Review the candidate campaign's targeting, bid strategy, product mix and coverage with Ad Operations. Campaign IDs are anonymous; different advertisers and objectives may be mixed, so cross-campaign CPA ranking is only a diagnostic shortlist.
3. Confirm daily coverage and tracking; zero-conversion days produce undefined CPA rather than a misleading zero. Historical subsampled data is not a current performance benchmark.
4. Propose an advertiser-specific, capped experiment only after comparable objectives and measurement are established. No spend shift, dollar return, realized lift, renewal, or upsell result is claimed.

## Conversion accounting
A conversion can be linked to many impressions. Summing the conversion flag would overcount sales. The source reuses {quality['conversion_ids_with_multiple_timestamps']:,} conversion IDs at different timestamps, so ID alone is not a sufficient event key. This project counts each credited (conversion_id, conversion_timestamp) pair once globally, allocating it to the most recent observed clicked credited impression, or the most recent credited impression if no clicked one is observed. This reporting rule does not recover an unknown platform touchpoint. CVR uses only the clicked subset; CPA uses all unique credited conversions. Filtering by day reports the allocated impression cohort with the source's observed follow-up outcomes, not conversions occurring on that calendar day.

## Integrity
{quality['accepted_rows']:,} accepted source rows; {quality['quarantined_rows']:,} rejected; {quality['repeated_credited_conversion_links_collapsed']:,} repeated credited conversion links collapsed. Identical source impressions are not automatically deleted because the source has no impression ID and distinct impressions can share published attributes. {quality['credited_conversion_keys_linked_to_multiple_campaigns']:,} credited conversion keys span more than one campaign and are allocated using the same explicit reporting rule. Published data contains campaign/day aggregates, not user IDs or conversion IDs.

## Measurement limits
Source costs are transformed and have no documented currency; revenue is absent. ROAS is unavailable. The cpo field is a transformed cost-per-order field, not revenue. No channel, region, demographic, calendar date or synthetic performance values are invented. Data is historical, anonymized and already subsampled by Criteo; findings describe the release rather than all live traffic. No sampling weights are supplied, so observed CTR/CVR cannot be used as population or industry benchmarks.

Source: {SOURCE_PAGE}
Dataset and derived data: CC BY-NC-SA 4.0. Attribution: Diemert, Meynet, Lefortier and Galland (2017), Attribution Modeling Increases Efficiency of Bidding in Display Advertising.
'''
    (output/'client_review.md').write_text(memo)
    con.close()
    print(json.dumps({'overall':total,'quality':quality},indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'docs')
    parser.add_argument('--from-source', type=Path, help='Verify and aggregate the full pinned gzipped TSV before rendering')
    args = parser.parse_args()
    if args.from_source:
        import_source(args.from_source)
    run(args.output)
