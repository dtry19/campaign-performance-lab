"""Deterministic synthetic campaign reporting; Python standard library only."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import random
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['date','campaign','channel','region','impressions','clicks','conversions','spend_cents','revenue_cents']
NUMERIC = FIELDS[4:]
CHANNELS = ['Display','Online Video','Mobile Web']
REGIONS = ['West','Central','East']

def generate():
    rng = random.Random(2027)
    rows = []
    for day in range(60):
        for campaign in range(18):
            channel = CHANNELS[campaign % 3]
            for region in REGIONS:
                impressions = rng.randint(18000, 42000)
                clicks = int(impressions * rng.uniform(.006, .018))
                # Designed heterogeneity, not an empirical advertising benchmark.
                conversion_rate = [.035,.022,.055][campaign % 3]
                if day >= 30 and channel == 'Online Video':
                    conversion_rate *= .55
                conversions = sum(rng.random() < conversion_rate for _ in range(clicks))
                spend = round(impressions / 1000 * [6,10,7][campaign % 3] * 100)
                revenue = conversions * rng.randint(6500,9500)
                rows.append(dict(zip(FIELDS,[(dt.date(2026,9,1)+dt.timedelta(days=day)).isoformat(),f'C{campaign+1:02}',channel,region,impressions,clicks,conversions,spend,revenue])))
    # Explicit fixtures exercise duplicate, missing dimension, funnel and spend checks.
    for i in range(3):
        rows.append(dict(rows[i]))
    for i, updates in enumerate([{'spend_cents':-10},{'clicks':999999},{'region':''},{'conversions':999999},{'date':'invalid'},{'impressions':'bad'}]):
        row = dict(rows[10+i]); row.update(updates); rows.append(row)
    return rows

def clean(rows):
    accepted, rejected, seen = [], [], set()
    for line, original in enumerate(rows,2):
        row = dict(original)
        reason = None
        try:
            dt.date.fromisoformat(row['date'])
            if row['channel'] not in CHANNELS or row['region'] not in REGIONS or not row['campaign']:
                raise ValueError('invalid dimension')
            for key in NUMERIC:
                row[key] = int(row[key])
            if min(row[k] for k in NUMERIC) < 0:
                raise ValueError('negative metric')
            if not row['impressions'] >= row['clicks'] >= row['conversions']:
                raise ValueError('invalid click-attributed funnel')
            key = tuple(row[k] for k in FIELDS[:4])
            if key in seen:
                raise ValueError('duplicate grain')
            seen.add(key)
        except (ValueError, TypeError, KeyError) as exc:
            reason = str(exc)
        if reason:
            rejected.append({'source_line':line,'reason':reason,'record':original})
        else:
            accepted.append(row)
    return accepted,rejected

def write_csv(path, rows, fields=None):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def database(rows, path):
    con=sqlite3.connect(path)
    con.execute('DROP TABLE IF EXISTS campaign_daily')
    con.execute('CREATE TABLE campaign_daily (date TEXT, campaign TEXT, channel TEXT, region TEXT, impressions INTEGER, clicks INTEGER, conversions INTEGER, spend_cents INTEGER, revenue_cents INTEGER, PRIMARY KEY(date,campaign,channel,region))')
    con.executemany('INSERT INTO campaign_daily VALUES (?,?,?,?,?,?,?,?,?)',[[r[k] for k in FIELDS] for r in rows])
    con.executescript((ROOT/'sql/metrics.sql').read_text())
    con.commit(); con.row_factory=sqlite3.Row
    return con

def run(output):
    output.mkdir(parents=True,exist_ok=True)
    raw=generate(); rows,rejected=clean(raw)
    write_csv(output/'campaign_raw.csv',raw,FIELDS)
    write_csv(output/'campaign_clean.csv',rows,FIELDS)
    (output/'quarantine.json').write_text(json.dumps(rejected,indent=2)+'\n')
    con=database(rows,output/'campaigns.sqlite')
    campaign=[dict(r) for r in con.execute('SELECT * FROM campaign_kpis ORDER BY roas DESC')]
    channels=[dict(r) for r in con.execute('SELECT * FROM channel_kpis ORDER BY roas DESC')]
    write_csv(output/'campaign_kpis.csv',campaign)
    quality={'source_rows':len(raw),'accepted_rows':len(rows),'quarantined_rows':len(rejected),'reasons':dict(Counter(r['reason'] for r in rejected))}
    payload={'rows':rows,'quality':quality}
    template=(ROOT/'src/dashboard.html').read_text()
    (output/'index.html').write_text(template.replace('__PAYLOAD__',json.dumps(payload)))
    (output/'quality.json').write_text(json.dumps(quality,indent=2)+'\n')
    best,worst=channels[0],channels[-1]
    shift=round(worst['spend']*.1,2)
    # Fixed observed return per dollar, illustrative only; no causal interpretation.
    scenario=round(shift*(best['roas']-worst['roas']),2)
    period=[dict(r) for r in con.execute('SELECT * FROM period_kpis')]
    write_csv(output/'period_kpis.csv',period)
    memo=f'''# Synthetic client business review

All results below come from a seeded simulation, not a T-Mobile campaign or client.

## Decision brief
- Highest observed channel ROAS: {best['channel']} ({best['roas']:.2f}x); lowest: {worst['channel']} ({worst['roas']:.2f}x).
- Investigate {worst['channel']} by campaign, region, creative and attribution lag before changing investment. The simulator deliberately introduces an Online Video conversion-rate decline after day 30; this is a test of detection, not a discovered real-world effect.
- Consider a capped experiment reallocating 10% of {worst['channel']} spend (${shift:,.2f}) toward {best['channel']}, subject to inventory, marginal costs and measurement checks.
- Holding observed average returns constant would imply ${scenario:,.2f} additional attributed revenue. This is scenario arithmetic, **not measured lift, incremental revenue, a forecast, or a causal estimate**.

## Reporting integrity
{len(rows):,} accepted records; {len(rejected)} quarantined out of {len(raw):,} input records. See quality.json and quarantine.json for auditable reasons. Monetary values use integer cents. All rates are ratios of summed components, never averages of row rates.

## Client discussion
1. Confirm the business objective and target CPA/ROAS with Customer Success; no client targets are assumed here.
2. Ask Ad Operations to review tracking, creative rotation, frequency and landing-page changes in the weaker segment.
3. Review the first/last 30-day comparison in period_kpis.csv and the dashboard; evaluate attribution lag before calling a decline.
4. Validate results with a controlled test and agreed success criteria before discussing expansion with Sales. Renewal or upsell is conditional on evidence and client goals.

## Measurement boundary
CVR is conversions/clicks; ROAS is attributed revenue/spend, not profit. Click-attributed conversions cannot exceed clicks in this fixture. No user-level data, attribution engine, actual DSP integration, CTV, DOOH, reach/frequency measurement or causal lift measurement is included. Cross-channel attribution comparability is an assumption of this simulation.
'''
    (output/'client_review.md').write_text(memo)
    (output/'summary.json').write_text(json.dumps({'quality':quality,'channels':channels,'scenario':{'shift_dollars':shift,'illustrative_revenue_difference':scenario}},indent=2)+'\n')
    con.close()
    print(json.dumps({'output':str(output),'quality':quality,'best_channel':best,'lowest_channel':worst},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=ROOT/'docs')
    run(parser.parse_args().output)
